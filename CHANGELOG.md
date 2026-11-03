## v0.1.2-rc.5 — Unreleased autonomous Live EPG

- Verify the IPTVnator Remote API programme time range against the real UTC clock; never trust completed programmes.
- On stale/missing Remote EPG, use current read-only XMLTV programme or the matching configured Xtream provider's schedule.
- Cache entire provider schedule (up to five minutes), selecting the current programme on every poll; recheck sooner when the cached schedule has ended.
- Preserve RC4 low-latency Live logo behaviour and RC3 archived Catch-up metadata, plus VOD/Trakt isolation and byte-identical wrapper.
- Add tests for stale Remote UI, exact programme boundary transitions and safe timezone handling.

## v0.1.2-rc.4 — Unreleased Live latency candidate

- Queue a new-channel request if a previous poll is in flight, preventing a missed file-loaded event and further 10-second wait.
- Retry transient logo failures after 8 seconds, rather than a 60-second lockout.
- Cache successful normalized logos in companion memory for 12 hours with a 16-MB cap; never cache failures.
- Skip unrelated Remote API/EPG calls for valid identity `/logo` requests.
- Preserve RC3 Catch-up, Live EPG, VOD isolation and byte-identical VLC wrapper.
- Add latency, cache and logo fast-path regression tests; Mac validation required.

## v0.1.2-rc.3 — Unreleased Catch-up title fix

- Recover selected Catch-up programme from exact server-clock timestamp in Xtream `timeshift` URL when IPTVnator provides channel-only title.
- Match imported XMLTV programme first; if missing, query configured provider's `get_simple_data_table` endpoint read-only with in-memory credentials only.
- Source identity must be unambiguous. Validate wall-clock, cap response size and timeout, forbid redirects/proxies and cache 90 seconds.
- Preserve Live title and logo, attached-artwork handling, VOD exclusion, and byte-identical VLC wrapper.
- Never attach unredacted IINA log files: other plugins may expose OAuth tokens, stream usernames and passwords.

## 0.1.2-rc.2 — Unreleased Catch-up and Live regression fix

- Restore Live TV and Catch-up metadata sync by removing reliance on browser `URL` / `URLSearchParams` globals inside IINA's JS runtime.
- Add runtime regression tests without `URL` injected into IINA sandbox; confirm VOD isolation and legacy/REST Catch-up.

- Recognize REST `/timeshift/.../streamId.ts` and legacy `/streaming/timeshift.php?stream=...` URLs.
- Accept `Channel - Selected Programme` Catch-up titles sent by IPTVnator.
- Keep Catch-up metadata fixed to the selected archived programme; do not copy current Live EPG Now.
- Restore channel logos for Catch-up while preserving existing Live and VOD behavior.
- Add Catch-up JavaScript/Python regression tests; no changes to VLC → IINA wrapper v1.1.

# Changelog

## v0.1.1 — First public beta (2026-11-03)

- Live EPG titles update within a playing IINA stream, including programmes with identical titles but different EPG start times. Observed in IINA 1.5.0 on macOS with IPTVnator 0.25 nightly.
- Channel logo as an mpv attached-picture image for macOS Now Playing.
- Transparent PNG logos are flattened onto a black background.
- Companion on localhost port 8766, reading IPTVnator Remote Control (8765) and local SQLite in read-only mode, with SQLite EPG fallback when the IPTVnator UI selects another channel.
- Existing VLC → IINA adapter v1.1 preserved byte-for-byte.
- Health-verified companion upgrade.

### Known limitations

- macOS **Control Center title** auto-refresh has not been confirmed. The experimental track-list refresh option is OFF by default and may affect PiP.
- Logo URLs that return 400/403/404 are not automatically replaced with an alternate channel logo (e.g. US: UP TV stream 23978).
- Channel identification uses Xtream stream ID plus name hint; collisions across playlists with the same ID and title remain possible.
- Local companion is macOS-specific; no HomeDocker server component is required.
