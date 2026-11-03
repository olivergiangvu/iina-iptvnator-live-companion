#!/usr/bin/env python3
"""Read-only companion for IINA Live title/artwork (localhost only).

Reads IPTVnator's Remote Control API and local content.poster_url. No Xtream
credentials, source URLs or playlist content are returned to IINA or logged.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import socket
import threading
import time
import zlib
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from contextlib import closing
from collections import OrderedDict
from datetime import datetime, timezone

from logo import flatten_png_black
from catchup import resolve_archive, resolve_live

DEFAULT_DB = Path.home() / ".iptvnator/databases/iptvnator.db"
IPTVNATOR_REMOTE = "http://127.0.0.1:8765/api/remote-control/status"
MAX_IMAGE_BYTES = 4_000_000
# Bounded in-memory normalized artwork cache: repeat channel launches never
# re-download or re-flatten the same image. Keys are hashes, not credential URLs.
LOGO_CACHE_TTL = 12 * 3600
LOGO_CACHE_CAP = 16_000_000
_LOGO_CACHE: OrderedDict[str, tuple[float, bytes, str]] = OrderedDict()
_LOGO_CACHE_LOCK = threading.Lock()


def stream_id(value: str) -> int | None:
    if not value or not value.isascii() or not value.isdigit() or len(value) > 15:
        return None
    number = int(value)
    return number if 0 < number < 2**53 else None


def remote_status() -> dict | None:
    try:
        with urllib.request.urlopen(IPTVNATOR_REMOTE, timeout=2.5) as response:
            if response.status != 200:
                return None
            data = json.load(response)
            return data if isinstance(data, dict) else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _db_uri(path: Path) -> str:
    return "file:" + urllib.parse.quote(str(path), safe="/") + "?mode=ro"


def _hint_matches(title: str, hint: str) -> bool:
    """Allow channel-only title, or a decorated EPG title from the VLC adapter."""
    title, hint = title.strip().casefold(), hint.strip().casefold()
    return bool(title and hint and (hint == title or
           any(hint.startswith(title + sep) for sep in (" · ", " | ", " — ", " - "))))


def lookup_channel(db_path: Path, stream: int, name: str = "", title_hint: str = "") -> dict | None:
    """Identity = Xtream numeric ID + launch title hint or active Remote name.

    Never accept an ID alone: several playlists can reuse the same Xtream IDs.
    On ambiguous duplicate IDs with distinct logos/EPG ids, refuse matching.
    """
    if not db_path.is_file() or (not name and not title_hint):
        return None
    try:
        with closing(sqlite3.connect(_db_uri(db_path), uri=True, timeout=1.0)) as db:
            rows = db.execute(
                "SELECT title, poster_url, epg_channel_id FROM content "
                "WHERE type='live' AND xtream_id=? LIMIT 150", (stream,)
            ).fetchall()
        matches = [(t, p, e) for t, p, e in rows if
                   (_hint_matches(str(t or ""), title_hint) if title_hint else
                    bool(name and str(t or "").strip().casefold() == name.strip().casefold()))]
        if not matches:
            return None
        identities = {(str(t or "").strip().casefold(), str(p or "").strip(),
                       str(e or "").strip()) for t, p, e in matches}
        if len(identities) > 1:
            return None  # avoid selecting the wrong provider/channel image
        title, logo, epg_id = matches[0]
        return {"title": str(title), "logo": str(logo or "").strip(),
                "epg_id": str(epg_id or "").strip()}
    except (sqlite3.DatabaseError, sqlite3.OperationalError, OSError):
        return None


def epg_from_sqlite(db_path: Path, channel: dict) -> dict:
    """Read currently-airing XMLTV programme; no external API/credentials needed."""
    empty = {"epgTitle": "", "epgStart": "", "epgEnd": ""}
    epg_id = channel.get("epg_id", "")
    if not db_path.is_file():
        return empty
    try:
        with closing(sqlite3.connect(_db_uri(db_path), uri=True, timeout=1.0)) as db:
            if not epg_id:
                rows = db.execute(
                    "SELECT DISTINCT id FROM epg_channels WHERE display_name=? LIMIT 2",
                    (channel["title"],)
                ).fetchall()
                if len(rows) != 1:
                    return empty
                epg_id = rows[0][0]
            row = db.execute(
                "SELECT title, start, stop FROM epg_programs "
                "WHERE channel_id=? AND datetime(start)<=datetime('now') "
                "AND datetime(stop)>datetime('now') "
                "ORDER BY start DESC LIMIT 1", (epg_id,)
            ).fetchone()
            if not row:
                return empty
            title, start, end = row
            def iso(v: str) -> str:
                value = str(v or "").strip().replace(" ", "T")
                if not value:
                    return ""
                # XMLTV is typically UTC ISO; add Z only when tz is absent.
                if value[-1:] not in ("Z", "z") and not (
                    "+" in value[10:] or "-" in value[10:]
                ):
                    value += "Z"
                return value
            return {"epgTitle": str(title or ""), "epgStart": iso(start), "epgEnd": iso(end)}
    except (sqlite3.DatabaseError, sqlite3.OperationalError, OSError):
        return empty


def current_epg(epg: dict, when: datetime | None = None) -> bool:
    """Only trust programmes whose start/end straddle the actual current UTC."""
    if not str(epg.get("epgTitle") or "").strip():
        return False
    try:
        begin = datetime.fromisoformat(str(epg.get("epgStart") or "").replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(epg.get("epgEnd") or "").replace("Z", "+00:00"))
        if begin.tzinfo is None or end.tzinfo is None:
            return False
        now = when or datetime.now(timezone.utc)
        return begin.astimezone(timezone.utc) <= now < end.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return False


def public_image_url(url: str) -> bool:
    """Images only from public HTTP(S) hosts; reject localhost/private net SSRF."""
    try:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            return False
        hostname = parts.hostname
        if hostname.lower() in ("localhost", "localhost.localdomain") or hostname.endswith(".local"):
            return False
        for entry in socket.getaddrinfo(hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM):
            address = ipaddress.ip_address(entry[4][0])
            if not address.is_global:
                return False
        return True
    except (ValueError, OSError, OverflowError):
        return False


class SafeImageRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not public_image_url(newurl):
            raise urllib.error.HTTPError(newurl, 403, "Image redirect blocked", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_image(url: str) -> tuple[bytes, str] | None:
    if not public_image_url(url):
        return None
    try:
        opener = urllib.request.build_opener(SafeImageRedirect())
        request = urllib.request.Request(url, headers={"User-Agent": "IPTVnatorLiveCompanion/0.1.2-rc.5"})
        with opener.open(request, timeout=8) as res:
            raw_content_type = res.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if raw_content_type not in ("image/jpeg", "image/png", "image/webp"):
                return None
            if int(res.headers.get("Content-Length") or "0") > MAX_IMAGE_BYTES:
                return None
            content = res.read(MAX_IMAGE_BYTES + 1)
            if not content or len(content) > MAX_IMAGE_BYTES:
                return None
            magic_ok = (content.startswith(b"\xff\xd8\xff") or
                        content.startswith(b"\x89PNG\r\n\x1a\n") or
                        (content.startswith(b"RIFF") and content[8:12] == b"WEBP"))
            if not magic_ok:
                return None
            if raw_content_type == "image/png":
                try:
                    return flatten_png_black(content), "image/png"
                except (ValueError, zlib.error):
                    return None  # never return transparent PNG as an opaque white tile
            if raw_content_type == "image/webp":
                return None  # can be transparent; only return artwork we know is opaque
            return content, raw_content_type
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None

def cached_image(url: str) -> tuple[bytes, str] | None:
    """Cache successful logo downloads. Never cache failures or URL credentials."""
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _LOGO_CACHE_LOCK:
        stored = _LOGO_CACHE.get(key)
        if stored and now - stored[0] < LOGO_CACHE_TTL:
            _LOGO_CACHE.move_to_end(key)
            return stored[1], stored[2]
        _LOGO_CACHE.pop(key, None)

    downloaded = download_image(url)
    if not downloaded:
        return None
    blob, mime = downloaded
    if len(blob) <= LOGO_CACHE_CAP:
        with _LOGO_CACHE_LOCK:
            _LOGO_CACHE[key] = (time.monotonic(), blob, mime)
            _LOGO_CACHE.move_to_end(key)
            while _LOGO_CACHE and sum(len(v[1]) for v in _LOGO_CACHE.values()) > LOGO_CACHE_CAP:
                _LOGO_CACHE.popitem(last=False)
    return downloaded


def catchup_program_title(channel_title: str, launch_title: str) -> str:
    """Selected Catch-up programme is fixed; never substitute the current Live EPG."""
    channel_title = (channel_title or "").strip()
    launch_title = (launch_title or "").strip()
    if not channel_title or not _hint_matches(channel_title, launch_title):
        return ""
    if launch_title.casefold() == channel_title.casefold():
        return ""
    for sep in (" - ", " · ", " | ", " — "):
        if (launch_title[:len(channel_title)].casefold() == channel_title.casefold()
                and launch_title[len(channel_title):].startswith(sep)):
            return launch_title[len(channel_title) + len(sep):].strip()
    return ""


class CompanionHandler(BaseHTTPRequestHandler):
    server_version = "IPTVnatorLiveCompanion/0.1.2-rc.5"
    sys_version = ""

    def log_message(self, fmt, *args):
        # No request path or URL logging; Xtream URLs/credentials stay private.
        return

    def json_response(self, code: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def state(self, stream: int, hint: str, playback: str = "live",
              archive_start: str = "") -> tuple[dict, dict | None]:
        remote = remote_status() or {}
        remote_name = str(remote.get("channelName") or "") if (
            remote.get("isLiveView") and remote.get("portal") == "xtream") else ""
        channel = lookup_channel(self.server.database_path, stream, remote_name, hint)
        if not channel:
            return {"isLiveView": True, "source": "unmatched"}, None
        if playback == "catchup":
            # The archived title is supplied by IPTVnator when opening the stream.
            # Do not overwrite with live Remote API "EPG Now" or current-time SQLite.
            selected_program = catchup_program_title(channel["title"], hint)
            epg = {"epgTitle": selected_program, "epgStart": "", "epgEnd": ""}
            epg_source = "catchup-title" if selected_program else "catchup-channel"
            if not selected_program and archive_start:
                resolved = resolve_archive(self.server.database_path, stream,
                                           channel["title"], archive_start)
                if resolved:
                    epg, epg_source = resolved
        else:
            # IPTVnator's Remote API can keep returning a completed programme
            # until its UI is clicked. Never trust stale EPG clock information.
            remote_is_same = bool(remote_name and remote_name.casefold() == channel["title"].casefold())
            remote_epg = {k: remote.get(k, "") for k in ("epgTitle", "epgStart", "epgEnd")}
            if remote_is_same and current_epg(remote_epg):
                epg, epg_source = remote_epg, "remote"
            else:
                local = epg_from_sqlite(self.server.database_path, channel)
                if current_epg(local):
                    epg, epg_source = local, "sqlite"
                else:
                    updated = resolve_live(self.server.database_path, stream, channel["title"])
                    if updated:
                        epg, epg_source = updated
                    elif remote_is_same and remote_epg.get("epgTitle"):
                        # Do not invent a current programme if both guides are
                        # missing. Keep last known title, explicitly mark stale.
                        epg, epg_source = remote_epg, "remote-stale"
                    else:
                        epg = {"epgTitle": "", "epgStart": "", "epgEnd": ""}
                        epg_source = "none"
        return {"isLiveView": True, "mode": playback, "source": epg_source,
                "channelName": channel["title"], **epg}, channel

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/health":
            return self.json_response(200, {"ok": True, "dbExists": self.server.database_path.is_file(),
                                            "version": "0.1.2-rc.5"})
        if u.path not in ("/status", "/logo"):
            return self.json_response(404, {"error": "not found"})
        params = urllib.parse.parse_qs(u.query)
        stream = stream_id(params.get("stream_id", [""])[0])
        hint = params.get("title_hint", [""])[0].strip()[:250]
        playback = params.get("playback", ["live"])[0]
        if playback not in ("live", "catchup"):
            return self.json_response(400, {"error": "invalid playback mode"})
        if stream is None:
            return self.json_response(400, {"error": "invalid stream_id"})
        archive_start = params.get("archive_start", [""])[0].strip()[:24]
        if u.path == "/logo" and hint:
            # Artwork identity requires only stream ID + launch channel name.
            # No EPG polling, provider archive lookup or 2.5s Remote API wait.
            channel = lookup_channel(self.server.database_path, stream, title_hint=hint)
            if not channel:
                _, channel = self.state(stream, hint, playback, archive_start)
            status = {}
        else:
            status, channel = self.state(stream, hint, playback, archive_start)
        matched = bool(channel)
        if u.path == "/status":
            return self.json_response(200, {
                "matched": matched,
                "isLiveView": bool(status.get("isLiveView")),
                "source": status.get("source", "unmatched"),
                "mode": playback,
                "channelName": status.get("channelName", "") if matched else "",
                "epgTitle": status.get("epgTitle", "") if matched else "",
                "epgStart": status.get("epgStart", "") if matched else "",
                "epgEnd": status.get("epgEnd", "") if matched else "",
                "hasLogo": bool(channel and channel["logo"]),
                "logoExt": (
                    ".jpg" if (channel and urllib.parse.urlsplit(channel["logo"]).path.lower().endswith((".jpg", ".jpeg")))
                    else ".png" if (channel and urllib.parse.urlsplit(channel["logo"]).path.lower().endswith(".png"))
                    else ".img"
                ),
                "logoTag": hashlib.sha256(channel["logo"].encode("utf-8")).hexdigest()[:12]
                           if channel and channel["logo"] else ""
            })
        if not matched or not channel["logo"]:
            return self.json_response(404, {"error": "channel logo unavailable"})
        result = cached_image(channel["logo"])
        if not result:
            return self.json_response(404, {"error": "image unavailable or blocked"})
        blob, content_type = result
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "private, max-age=180")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(blob)


def main():
    parser = argparse.ArgumentParser(description="IPTVnator Live Companion read-only local server")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), CompanionHandler)
    server.database_path = args.db.expanduser()
    print(f"Live Companion listening on 127.0.0.1:{args.port}; DB exists={server.database_path.is_file()}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
