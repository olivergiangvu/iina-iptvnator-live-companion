# Architecture

[Home](../README.md) · [Installation](INSTALLATION.md) · [Metadata Companion](METADATA_COMPANION.md) · [Security](../SECURITY.md)

## Component boundaries

```text
IPTVnator (Xtream source)
  ├─ External Player (VLC arguments) ──► launcher v1.1 ──► IINA/mpv playback
  │                                                        ▲
  ├─ Local Remote API :8765 ───┐                            │
  └─ Read-only SQLite/EPG ─────┼──► Python service :8766 ◄──┤
Configured Xtream EPG ─────────┘             ▲              │
                                             └── IINA plugin main.js
                                                    ├─ media title
                                                    └─ channel attached-picture
                                                       → macOS Now Playing
```

The launcher changes how the **player is invoked**. The metadata service and IINA plugin only enrich the player title and artwork. They do not replace IPTVnator, modify its database, transcode streams or create an alternative player.

## Metadata lifecycle

**Identity:** IINA plugin parses Live URLs and both Xtream Catch-up styles (REST `/timeshift/...` and legacy `/streaming/timeshift.php`). It sends only stream ID, launch-title hint, playback mode and a validated archive-start clock to the localhost service. Stream URLs/usernames/passwords are **not** passed to that API. The service rejects ambiguous stream/channel matches.

**Live:** every ~10 seconds, IINA asks for programme metadata. The Companion accepts IPTVnator Remote EPG only while its actual start/end bracket the current time; otherwise it tries current read-only XMLTV and then a cached list from the configured Xtream provider. Each request selects the current show by the clock — **no IPTVnator click required**.

**Catch-up:** the Companion uses the original archive start to locate the historical programme (local XMLTV first, then provider's guide), retaining its title and broadcast window. Provider timezone is applied only when known; no time is invented from video position.

**Artwork:** `/logo` independently resolves channel identity and fetches/normalizes a supported channel image. The Python service uses a bounded in-memory successful-image cache. IINA attaches the image as an mpv `attached-picture` track; it is **not** composited into the actual video.

**Now Playing:** IINA owns Control Center and PiP. A change to mpv media title does not guarantee immediate Control Center refresh. The optional experimental artwork-track reattachment is disabled by default; do not assume perfectly synchronized native Now Playing on all macOS versions.

## Data and security boundaries

- SQLite connections are read-only; no changes to IPTVnator content or EPG tables.
- Local API listens only on `127.0.0.1:8766`; Remote API remains on `127.0.0.1:8765`.
- Provider credentials are used only inside the Python service to query the **configured provider**. They are not returned to IINA plugin responses or logged by our service.
- Network responses are bounded by size/time, and sensitive URLs are not part of the emitted diagnostics.
- The launcher v1.1 remains byte-identical and independently versioned; VOD, EP+/Trakt, native playback and manually controlled PiP remain separate.

## Known limits

An ambiguous provider mapping, absent historical EPG or unreachable image may produce a channel-only title or no logo. Source-provider collisions cannot always be distinguished solely from numeric Xtream stream ID and channel title. See [Security](../SECURITY.md) and [Testing](TESTING.md).
