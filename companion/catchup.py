"""Resolve the selected archived Xtream programme without logging credentials.

Read-only SQLite first; if unavailable, fetch a bounded EPG response from the
same configured Xtream panel. Credentials remain inside this localhost server.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from threading import Lock
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ARCHIVE_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}:\d{2}-\d{2}$")
_OFFSET_RE = re.compile(r"^UTC([+-])(\d{2}):(\d{2})$")
_CACHE: dict[tuple[str, int, str], tuple[float, tuple[dict, str] | None]] = {}
_CACHE_TTL = 90.0
_MAX_RESPONSE = 6_000_000


def parse_start(value: str) -> dt.datetime | None:
    if not isinstance(value, str) or not _ARCHIVE_RE.fullmatch(value):
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%d:%H-%M")
    except ValueError:
        return None


def server_zone(name: str) -> dt.tzinfo | None:
    if not name or len(name) > 90:
        return None
    matched = _OFFSET_RE.fullmatch(name)
    if matched:
        minutes = int(matched[2]) * 60 + int(matched[3])
        if minutes > 14 * 60 or int(matched[3]) >= 60:
            return None
        if matched[1] == "-":
            minutes = -minutes
        return dt.timezone(dt.timedelta(minutes=minutes))
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError, KeyError):
        return None


def _db_uri(db_path: Path) -> str:
    return "file:" + urllib.parse.quote(str(db_path), safe="/") + "?mode=ro"


def _source(db_path: Path, stream: int, title: str) -> dict | None:
    """Only an unambiguous ID + channel + provider binding may be queried."""
    try:
        with closing(sqlite3.connect(_db_uri(db_path), uri=True, timeout=1)) as db:
            rows = db.execute("""
                SELECT p.id, p.serverUrl, p.username, p.password, p.userAgent,
                       p.payload, c.epg_channel_id
                FROM content AS c
                JOIN categories AS cat ON cat.id = c.category_id
                JOIN playlists AS p ON p.id = cat.playlist_id
                WHERE c.type='live' AND c.xtream_id=? AND c.title=?
                LIMIT 5
            """, (stream, title)).fetchall()
        unique = {str(row[0]): row for row in rows}
        if len(unique) != 1:
            return None
        row = next(iter(unique.values()))
        try:
            payload = json.loads(row[5]) if row[5] else {}
            tzname = payload.get("serverTimezone", "") if isinstance(payload, dict) else ""
        except (ValueError, TypeError):
            tzname = ""
        return {"playlist": str(row[0]), "server": str(row[1] or ""),
                "username": str(row[2] or ""), "password": str(row[3] or ""),
                "useragent": str(row[4] or ""),
                "zone": server_zone(str(tzname or "")),
                "epg_id": str(row[6] or "")}
    except (sqlite3.Error, OSError, TypeError):
        return None


def _iso_utc(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if not parsed.tzinfo:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _iso(value: dt.datetime | None) -> str:
    return (value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            if value else "")


def _local_epg(db_path: Path, source: dict, title: str,
               start: dt.datetime) -> dict | None:
    zone = source["zone"]
    if not zone:
        return None  # do not guess the provider's timezone
    epg_id = source["epg_id"]
    utc = start.replace(tzinfo=zone).astimezone(dt.timezone.utc).isoformat()
    try:
        with closing(sqlite3.connect(_db_uri(db_path), uri=True, timeout=1)) as db:
            if not epg_id:
                ids = db.execute(
                    "SELECT DISTINCT id FROM epg_channels WHERE display_name=? LIMIT 2",
                    (title,)).fetchall()
                if len(ids) != 1:
                    return None
                epg_id = ids[0][0]
            rows = db.execute("""
                SELECT title, start, stop FROM epg_programs
                WHERE channel_id=? AND datetime(start)>=datetime(?, '-1 day')
                    AND datetime(start)<=datetime(?, '+1 day')
                LIMIT 1500
            """, (epg_id, utc, utc)).fetchall()
    except (sqlite3.Error, OSError):
        return None
    matches = []
    for name, begin, end in rows:
        instant = _iso_utc(begin)
        if instant and instant.astimezone(zone).strftime("%Y-%m-%d:%H-%M") == start.strftime("%Y-%m-%d:%H-%M"):
            matches.append({"epgTitle": str(name or "").strip(),
                            "epgStart": _iso(instant),
                            "epgEnd": _iso(_iso_utc(end))})
    return matches[0] if len(matches) == 1 and matches[0]["epgTitle"] else None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _provider_rows(source: dict, stream: int) -> list[dict]:
    base = urllib.parse.urlsplit(source["server"])
    if (base.scheme not in ("http", "https") or not base.hostname or
            base.username or base.password or base.query or base.fragment or
            not source["username"] or not source["password"]):
        return []
    path = base.path.rstrip("/")
    if path.endswith("/player_api.php"):
        path = path[:-len("/player_api.php")]
    endpoint = urllib.parse.urlunsplit((
        base.scheme, base.netloc, path + "/player_api.php", "", ""))
    params = urllib.parse.urlencode({
        "username": source["username"], "password": source["password"],
        "action": "get_simple_data_table", "stream_id": str(stream)})
    # Requests only the playlist's configured panel; never follows redirects
    # and never routes credential-bearing requests through an OS HTTP proxy.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(endpoint + "?" + params, headers={
        "User-Agent": source["useragent"].strip() or "IPTVnatorLiveCompanion/0.1.2",
        "Accept": "application/json"})
    try:
        with opener.open(request, timeout=4.0) as response:
            if (response.status != 200 or
                    int(response.headers.get("Content-Length") or "0") > _MAX_RESPONSE):
                return []
            raw = response.read(_MAX_RESPONSE + 1)
            if len(raw) > _MAX_RESPONSE:
                return []
        body = json.loads(raw)
        entries = body.get("epg_listings", []) if isinstance(body, dict) else []
        if isinstance(entries, dict):
            entries = list(entries.values())
        return [x for x in entries[:5000] if isinstance(x, dict)] if isinstance(entries, list) else []
    except (OSError, urllib.error.URLError, urllib.error.HTTPError,
            ValueError, TypeError, OverflowError):
        return []


def _decode_title(raw: object) -> str:
    text = str(raw or "").strip()
    try:
        if text and len(text) % 4 == 0 and re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", text):
            decoded = base64.b64decode(text, validate=True).decode("utf-8")
            if decoded and all(ch.isprintable() for ch in decoded):
                return decoded.strip()[:250]
    except (ValueError, UnicodeError):
        pass
    return text[:250]


def _provider_epg(rows: list[dict], start: dt.datetime,
                  zone: dt.tzinfo | None) -> dict | None:
    matches = []
    wanted = start.strftime("%Y-%m-%d %H:%M")
    for row in rows:
        panel_start = str(row.get("start") or "").strip().replace("T", " ")
        if not panel_start and zone:
            try:
                unix = int(row.get("start_timestamp", 0))
                if 946684800 <= unix <= 4102444800:
                    panel_start = dt.datetime.fromtimestamp(
                        unix, zone).strftime("%Y-%m-%d %H:%M")
            except (TypeError, ValueError, OverflowError):
                pass
        if panel_start[:16] != wanted:
            continue
        title = _decode_title(row.get("title"))
        if not title:
            continue

        def from_unix(key):
            try:
                value = int(row.get(key, 0))
                if 946684800 <= value <= 4102444800:
                    return _iso(dt.datetime.fromtimestamp(
                        value, dt.timezone.utc))
            except (TypeError, ValueError, OverflowError):
                pass
            return ""

        matches.append({"epgTitle": title,
                        "epgStart": from_unix("start_timestamp"),
                        "epgEnd": from_unix("stop_timestamp")})
    return matches[0] if len(matches) == 1 else None


def resolve_archive(db_path: Path, stream: int, title: str,
                    archive_start: str) -> tuple[dict, str] | None:
    """Resolve exact selected programme, never today's Live Now programme."""
    start = parse_start(archive_start)
    if not start:
        return None
    source = _source(db_path, stream, title)
    if not source:
        return None
    key = (source["playlist"], stream, archive_start)
    cached = _CACHE.get(key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL:
        return cached[1]
    local = _local_epg(db_path, source, title, start)
    result = (local, "catchup-sqlite") if local else None
    if not result:
        remote = _provider_epg(_provider_rows(source, stream),
                               start, source["zone"])
        if remote:
            result = (remote, "catchup-provider")
    if len(_CACHE) > 128:
        _CACHE.clear()
    _CACHE[key] = (time.monotonic(), result)
    return result


# Live schedule cache stores a programme LIST rather than one now-playing item.
# That permits local clock transitions even if IPTVnator's Remote API is stale.
_LIVE_CACHE: dict[tuple[str, int], tuple[float, list[dict]]] = {}
_LIVE_CACHE_LOCK = Lock()
_LIVE_TTL = 300.0
_LIVE_NEGATIVE_TTL = 40.0


def _provider_time(row: dict, timestamp_key: str, clock_key: str,
                   zone: dt.tzinfo | None) -> dt.datetime | None:
    """Prefer unambiguous Xtream Unix timestamps; never guess a naive timezone."""
    try:
        raw = int(row.get(timestamp_key, 0))
        if 946684800 <= raw <= 4102444800:
            return dt.datetime.fromtimestamp(raw, tz=dt.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    clock = str(row.get(clock_key) or "").strip()
    if not clock:
        return None
    try:
        value = dt.datetime.fromisoformat(clock.replace("Z", "+00:00"))
        if value.tzinfo is None:
            if zone is None:
                return None
            value = value.replace(tzinfo=zone)
        return value.astimezone(dt.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _live_schedule(rows: list[dict], zone: dt.tzinfo | None) -> list[dict]:
    schedule: list[dict] = []
    for row in rows:
        begin = _provider_time(row, "start_timestamp", "start", zone)
        end = _provider_time(row, "stop_timestamp", "stop", zone)
        if end is None:
            end = _provider_time(row, "stop_timestamp", "end", zone)
        title = _decode_title(row.get("title"))
        if not (begin and end and begin < end and title):
            continue
        schedule.append({"epgTitle": title, "epgStart": _iso(begin),
                         "epgEnd": _iso(end), "_start": begin, "_end": end})
    return sorted(schedule, key=lambda item: item["_start"])


def resolve_live(db_path: Path, stream: int, channel_title: str,
                 at: dt.datetime | None = None) -> tuple[dict, str] | None:
    """Read the configured provider's schedule, select airing item by clock.

    A cached schedule is evaluated with the current time on EVERY poll, even
    when no network request occurs. No Xtream credentials leave this server.
    """
    now = at or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)
    source = _source(db_path, stream, channel_title)
    if not source:
        return None
    key = (source["playlist"], stream)
    instant = time.monotonic()
    with _LIVE_CACHE_LOCK:
        cached = _LIVE_CACHE.get(key)
    if cached and instant - cached[0] < (
            _LIVE_TTL if cached[1] else _LIVE_NEGATIVE_TTL):
        schedule = cached[1]
    else:
        schedule = _live_schedule(_provider_rows(source, stream), source["zone"])
        with _LIVE_CACHE_LOCK:
            if len(_LIVE_CACHE) >= 32:
                _LIVE_CACHE.clear()
            _LIVE_CACHE[key] = (time.monotonic(), schedule)
    current = [p for p in schedule if p["_start"] <= now < p["_end"]]
    if len(current) != 1:
        return None
    selected = current[0]
    return ({k: selected[k] for k in ("epgTitle", "epgStart", "epgEnd")},
            "live-provider")
