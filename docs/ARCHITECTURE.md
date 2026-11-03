# Architecture — IPTVnator Live Companion v0.1.2

## Data flow

    IPTVnator (Xtream playlist, SQLite, Remote API :8765)
        ├─ Original external VLC → IINA wrapper v1.1 → IINA/mpv playback
        └─ Local EPG / logo metadata
                  ↓
    Python Companion (loopback :8766; read-only SQLite)
        ├─ Live: current clock-validated Remote EPG
        │        else current XMLTV; else cached Xtream provider schedule
        ├─ Catch-up: archived programme by selected timeshift start
        │            via historical XMLTV or Xtream provider EPG
        └─ Artwork: safe fetch, bounded in-memory cache, opaque black PNG
                  ↓
    IINA Live Companion plugin (10-second polling)
        ├─ Verify numeric stream ID and channel launch title
        ├─ File-local mpv title: channel · show (local HH:mm–HH:mm)
        └─ mpv attached-picture track for native macOS Now Playing

## Invariants

- No modifications to the v1.1 VLC → IINA wrapper, playback/codec, PiP or other IINA plugins.
- No writes to IPTVnator SQLite. All source credentials and URLs remain server-side.
- Companion only binds localhost, with bounded provider EPG and image fetching.
- Live uses the actual time to transition independently of IPTVnator UI; Catch-up remains fixed to selected archive programme.
- When guide times/timezone are unavailable or ambiguous, do not invent dates.
- The optional experimental native Control Center refresh remains disabled by default.

## Verification

See [release acceptance](CATCHUP_FIX_TEST.md), [security](../SECURITY.md), and GitHub Actions.
