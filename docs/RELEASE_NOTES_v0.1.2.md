# v0.1.2 — First Stable Release (2026-11-03)

macOS · IINA 1.5.0 · IPTVnator Xtream

## Highlights

- **Live TV:** show title and original broadcast window; automatic EPG changes without clicking IPTVnator, with current-clock validation and local/provider schedule fallbacks.
- **Catch-up:** historical programme identity and original broadcast window for REST/legacy timeshift streams, when reliable guide times are available.
- **Artwork:** channel logo in native macOS Now Playing, improved cache and retry handling.
- **Compatibility:** no changes to the original VLC → IINA launcher v1.1, video playback, manual PiP or VOD/EP+/Trakt workflows.

## Official Release downloads

The [v0.1.2 GitHub Release](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.2) distributes three **separate** assets:

| Asset | Install target |
| --- | --- |
| `IPTVnator-Live-Companion-0.1.2.iinaplgz` | IINA → Settings → Plugins |
| `iptvnator-iina-vlc` (v1.1) | `~/.local/bin/iptvnator-iina-vlc` |
| `IPTVnator-Metadata-Companion-0.1.2.tar.gz` | Permanent source directory + macOS user LaunchAgent |

The two additional standalone distribution assets were attached **after the initial release tag**; that immutable source tag predates some helper scripts found in today's `main`. Prefer [Installation](INSTALLATION.md) for the complete current setup rather than copying steps from the original tag.

**Existing deployments:** keep the launcher unchanged; update Companion source and restart its LaunchAgent. Update the IINA plugin separately when its version changes. See [Operations](OPERATIONS.md).

## Verification

Python/JavaScript regressions and GitHub Actions passed. Live EPG rollover without IPTVnator UI interaction, Catch-up title/broadcast hours and channel artwork were also tested on IINA 1.5.0/macOS.

## Known limits

- Provider EPG history, timezone and image URLs may be incomplete or unavailable.
- IINA decides native Control Center refresh timing. Optional experimental track-list refresh remains off by default for PiP safety.
- Intended for a single Mac and loopback API, not a public server.

[Changelog](../CHANGELOG.md) · [Security](../SECURITY.md)
