# IPTVnator Live Companion v0.1.1 — First Public Beta

Native IINA 1.5.0 companion for IPTVnator 0.25 nightly on macOS.

**Highlights**
- Dynamic Live TV EPG title in IINA, with programme start/end times (verified on macOS).
- Channel logo in macOS Now Playing using mpv `attached-picture`.
- Black background for transparent PNG channel logos.
- Non-destructive VLC → IINA wrapper v1.1 compatibility; manual PiP unchanged.
- Local Python companion with read-only SQLite lookup and EPG fallback.

**Install**

Download `IPTVnator-Live-Companion-0.1.1.iinaplgz` below and follow the [README](https://github.com/olivergiangvu/iina-iptvnator-live-companion#readme) for installing the localhost companion and IINA plugin.

**Known limitations**: Control Center title update on programme boundary is not independently verified; experimental refresh is opt-in. Broken upstream channel logo URLs have no automatic alternate-channel fallback. Windows/Linux and non-Xtream sources are not covered.

**Version**: v0.1.1 · **License**: MIT · **Source**: `main` branch.
