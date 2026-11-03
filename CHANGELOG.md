# Changelog

## v0.1.2 — Stable (2026-11-03)

- First stable release tested on IINA 1.5.0 with IPTVnator Xtream Live and Catch-up.
- Live titles auto-update across programme boundaries without clicking IPTVnator: validate current Remote EPG; fall back to read-only XMLTV and cached provider schedule.
- Catch-up REST/legacy timeshift support with historical programme identity and real scheduled start/end, converted to local time when source timezone is reliable.
- Native IINA/mpv channel artwork in Now Playing; optimized cache, retry and fast path for repeated channel launches.
- Protect Live/VOD isolation, EP+/Trakt, PiP and byte-identical VLC → IINA wrapper v1.1.
- Security: localhost-only, read-only SQLite, provider credentials kept server-side, bounded remote EPG/image downloads.
- Automated Python and JavaScript tests, GitHub Actions and release artifact verification.

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
