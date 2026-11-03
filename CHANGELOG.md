# Changelog

## v0.1.2 — Stable (2026-11-03)

- **Live EPG:** programme titles and original broadcast hours update at a programme boundary without requiring IPTVnator UI interaction. Expired Remote EPG is replaced with current XMLTV or a cached provider schedule when available.
- **Catch-up:** recognizes REST and legacy Xtream timeshift streams, preserving the selected archived programme and its real scheduled broadcast window when the provider supplies reliable times.
- **Artwork:** channel logos in native macOS Now Playing, black-backed transparent PNG handling, bounded successful-image cache and faster retries/channel switching.
- **Compatibility:** original VLC → IINA launcher **v1.1 stays byte-identical**; no interception of VOD/Trakt/EP+, and PiP remains controlled by IINA.
- **Distribution:** three separate official assets — launcher, IINA `.iinaplgz` plugin and Python Metadata Companion `.tar.gz` source — with explicit lifecycle scripts and tests. These distribution helpers were added to `main` **after** the immutable v0.1.2 source tag.
- **Quality:** Python/JavaScript regressions and GitHub Actions checks for plugin/archive content, installer non-overwrite behaviour and original launcher checksum.

**Limitations:** provider EPG and artwork may be missing; Control Center refresh remains dependent on IINA. See [README](README.md) and [Security](SECURITY.md).

## v0.1.1 — First public beta (2026-11-03)

- Dynamic Live EPG titles in IINA, including broadcast hours.
- Channel artwork in macOS Now Playing using mpv attached-picture.
- Transparent PNG logos normalized over black.
- Read-only localhost Python Companion (`:8766`) with IPTVnator Remote API (`:8765`) and SQLite fallback.
- Original launcher v1.1 preserved and Companion restart health-checked.

See the [v0.1.1 release](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.1) for the historical beta. The early beta did not yet support the complete stable Live/Catch-up behaviour described above.
