"use strict";
/* IPTVnator Live Companion — IINA main entry. One instance per player. */
const { core, mpv, event, http, file, utils, menu, console: log } = iina;
const API = "http://127.0.0.1:8766";
const INTERVAL_MS = 10000;
const ART_TITLE = "IPTVnator Live Companion logo";
let enabled = true;
let posterEnabled = true;
let nativeRefreshEnabled = false; // opt-in: experimental mpv track-list refresh of Control Center
let generation = 0;
let currentUrl = "";
let ownerChannel = "";
let lastEpgKey = "";
let lastTitle = "";
let artworkKey = "";
let artworkFile = "";
let artworkRetryAt = 0;
let polling = false;
let initialMediaTitle = "";
let lastSyncDiagnostic = "";
let nativeRefreshBusy = false;

function debug(message) { log.log("[IPTVnator Live] " + message); }
function getUrl() { try { return String(core.status.url || ""); } catch (_) { return ""; } }
function getMpvString(key) { try { return String(mpv.getString(key) || ""); } catch (_) { return ""; } }
function streamIdFromUrl(url) {
  // Never persist or log raw stream URLs: Xtream URLs may contain login credentials.
  if (!/^https?:\/\//i.test(url)) return null;
  let pathname;
  try { pathname = new URL(url).pathname; } catch (_) {
    pathname = url.split(/[?#]/)[0].replace(/^https?:\/\/[^/]+/i, "");
  }
  if (/\/(movie|series)\//i.test(pathname)) return null;
  // A bare .mp4 URL is likely VOD; accept .mp4 only inside Xtream /live/.
  if (/\.mp4\/?$/i.test(pathname) && !/\/live\//i.test(pathname)) return null;
  const match = pathname.match(/\/(\d+)(?:\.(?:ts|m3u8|m3u|mp4))?\/?$/i);
  return match ? match[1] : null;
}
function signature(obj) {
  return [obj.channelName || "", obj.epgStart || "", obj.epgEnd || "", obj.epgTitle || ""].join("\u001f");
}
function localTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false });
}
function displayTitle(info) {
  const channel = String(info.channelName || "").trim();
  const program = String(info.epgTitle || "").trim();
  if (!program) return channel;
  const start = localTime(info.epgStart);
  const end = localTime(info.epgEnd);
  const clock = start && end ? ` (${start}–${end})` : "";
  return `${channel} · ${program}${clock}`;
}
function parseResponse(res) {
  if (!res || Number(res.statusCode) !== 200) return null;
  try { return typeof res.data === "object" && res.data !== null ? res.data : JSON.parse(res.text); }
  catch (_) { return null; }
}
async function limited(promise, ms) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error("request timeout")), ms);
      })
    ]);
  } finally { if (timer) clearTimeout(timer); }
}
function safeTracks() { try { return mpv.getNative("track-list") || []; } catch (_) { return []; } }
function ownTracks() {
  return safeTracks().filter(t => t && t.type === "video" && t.albumart === true &&
    (t.title === ART_TITLE || (artworkFile && t["external-filename"] === artworkFile)));
}
function removeOwnArtwork() {
  for (const t of ownTracks()) {
    try { mpv.command("video-remove", [String(t.id)]); } catch (_) { /* best effort */ }
  }
  artworkFile = "";
  artworkKey = "";
}
function invalidate() {
  generation += 1;
  currentUrl = "";
  ownerChannel = "";
  lastEpgKey = "";
  lastTitle = "";
  initialMediaTitle = "";
  artworkRetryAt = 0;
  nativeRefreshBusy = false;
  // file-local tracks are released by mpv between media files.
  artworkFile = "";
  artworkKey = "";
}
async function applyArtwork(info, streamId, token) {
  if (!posterEnabled || !info.hasLogo || Date.now() < artworkRetryAt) return;
  const key = `${streamId}:${info.channelName}:${info.logoTag || ""}`;
  if (artworkKey === key) return;
  artworkRetryAt = Date.now() + 60000;
  const ext = [".png", ".jpg"].includes(info.logoExt) ? info.logoExt : ".img";
  const temp = `@tmp/iptvnator-logo-${Date.now()}-${token}${ext}`;
  const logoURL = `${API}/logo?stream_id=${encodeURIComponent(streamId)}&title_hint=${encodeURIComponent(initialMediaTitle)}`;
  try {
    await limited(http.download(logoURL, temp), 11000);
    if (generation !== token || getUrl() !== currentUrl || !file.exists(temp)) return;
    const absolute = String(utils.resolvePath(temp) || "");
    if (!absolute.startsWith("/")) return;
    const originalVid = getMpvString("vid");
    removeOwnArtwork();
    mpv.command("video-add", [absolute, "auto+attached-picture", ART_TITLE]);
    artworkKey = key;
    artworkFile = absolute;
    setTimeout(() => {
      if (generation !== token || getUrl() !== currentUrl) return;
      const found = safeTracks().some(t =>
        t && t.type === "video" && t.albumart === true &&
        t["external-filename"] === absolute
      );
      const nowVid = getMpvString("vid");
      if (originalVid && nowVid && originalVid !== nowVid) {
        try { mpv.set("vid", originalVid); } catch (_) {}
      }
      debug(found ? "Channel logo attached to mpv (check native Now Playing)."
                  : "Album-art track not verified; check IINA logs.");
    }, 900);
  } catch (err) {
    // Provider may not supply a downloadable logo; title sync continues.
    debug("Artwork unavailable: " + (err && err.message ? err.message : "download error"));
  }
}
function requestNativeNowPlayingRefresh(ticket, url) {
  // IINA 1.5.0 updates macOS Now Playing with title after video track-list changes.
  // The safe opt-in signal re-attaches *our own* album-art track (never main video).
  if (!nativeRefreshEnabled || !posterEnabled || nativeRefreshBusy || !artworkFile) return;
  const previous = ownTracks();
  if (previous.length !== 1 || previous[0].id == null) return;
  const oldId = String(previous[0].id);
  const originalVid = getMpvString("vid");
  nativeRefreshBusy = true;
  try {
    mpv.command("video-add", [artworkFile, "auto+attached-picture", ART_TITLE]);
    setTimeout(() => {
      try {
        if (generation !== ticket || getUrl() !== url) return;
        const current = ownTracks();
        const fresh = current.some(t => String(t.id) !== oldId);
        if (fresh) {
          mpv.command("video-remove", [oldId]);
          debug("Requested native Now Playing refresh via attached artwork track.");
        } else {
          debug("Native refresh skipped: no new artwork track found.");
        }
        const vid = getMpvString("vid");
        if (originalVid && vid && vid !== originalVid) {
          mpv.set("vid", originalVid);
        }
      } catch (_) {
        debug("Native refresh failed; playback untouched.");
      } finally { nativeRefreshBusy = false; }
    }, 500);
  } catch (_) { nativeRefreshBusy = false; }
}

async function poll() {
  if (!enabled || polling) return;
  const url = getUrl();
  const streamId = streamIdFromUrl(url);
  if (!url || !streamId) return;
  if (url !== currentUrl) {
    invalidate();
    currentUrl = url;
    initialMediaTitle = getMpvString("force-media-title") || String(core.status.title || "");
    lastSyncDiagnostic = "";
  }
  const ticket = generation;
  polling = true;
  try {
    const statusURL = `${API}/status?stream_id=${encodeURIComponent(streamId)}&title_hint=${encodeURIComponent(initialMediaTitle)}`;
    const data = parseResponse(await limited(http.get(statusURL, {}), 7000));
    if (generation !== ticket || getUrl() !== url) return;
    if (!data || !data.matched || !data.isLiveView) {
      const key = data ? `unmatched:${data.source || "unknown"}` : "offline";
      if (lastSyncDiagnostic !== key) {
        lastSyncDiagnostic = key;
        debug(`No Live metadata association (${key}). Wrapper title preserved.`);
      }
      return;
    }
    if (lastSyncDiagnostic !== "linked") {
      lastSyncDiagnostic = "linked";
      debug(`Live metadata association OK (EPG source=${data.source || "unknown"}).`);
    }
    if (ownerChannel && ownerChannel !== data.channelName) return;
    if (!ownerChannel) {
      // The wrapper's initial title is typically the channel name; IPTVnator can
      // alternatively supply EPG title. The server verifies stream ID + channel.
      ownerChannel = String(data.channelName || "");
      debug("Linked player to IPTVnator Live channel; no URLs logged.");
    }
    const key = signature(data);
    if (key !== lastEpgKey) {
      lastEpgKey = key;
      const title = displayTitle(data);
      if (title && title !== lastTitle) {
        try {
          mpv.set("file-local-options/force-media-title", title);
          lastTitle = title;
          debug("Set EPG title (file-local) on mpv.");
          setTimeout(() => {
            if (generation !== ticket || getUrl() !== url) return;
            const actual = getMpvString("media-title");
            if (actual && actual !== title) {
              debug("mpv media-title differs after update; native Now Playing may not refresh.");
            }
          }, 500);
          // Defer after mpv title propagation; a track-list event asks IINA
          // to refresh the native macOS Now Playing title withTitle=true.
          setTimeout(() => {
            if (generation === ticket && getUrl() === url) requestNativeNowPlayingRefresh(ticket, url);
          }, 650);
        } catch (err) {
          debug("Title write failed; launcher title retained.");
        }
      }
    }
    if (posterEnabled && !artworkKey) void applyArtwork(data, streamId, ticket);
  } catch (_) {
    // No companion/IPTVnator: leave the original media title untouched.
  } finally { polling = false; }
}
const menuEnabled = menu.item("Live EPG title sync", () => {
  enabled = !enabled;
  menuEnabled.selected = enabled;
  menu.forceUpdate();
  if (enabled) void poll();
}, { selected: true });
const menuArtwork = menu.item("Live channel logo in Now Playing", () => {
  posterEnabled = !posterEnabled;
  menuArtwork.selected = posterEnabled;
  menu.forceUpdate();
  if (!posterEnabled) removeOwnArtwork();
  else void poll();
}, { selected: true });
const menuRefresh = menu.item("Experimental: refresh Control Center on EPG change", () => {
  nativeRefreshEnabled = !nativeRefreshEnabled;
  menuRefresh.selected = nativeRefreshEnabled;
  menu.forceUpdate();
}, { selected: false });
menu.addItem(menuEnabled);
menu.addItem(menuArtwork);
menu.addItem(menuRefresh);

event.on("mpv.file-loaded", () => { invalidate(); void poll(); });
event.on("mpv.end-file", () => { invalidate(); });
setInterval(() => { void poll(); }, INTERVAL_MS);
debug("Loaded. Live playback only; Trakt/EP+ VOD sessions are out of scope.");

// Unit tests may use these helpers without IINA's runtime through a separate module.
