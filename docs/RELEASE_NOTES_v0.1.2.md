# IPTVnator Live Companion v0.1.2 — Stable

**First stable release** for IINA 1.5.0 and IPTVnator Xtream on macOS.

## What's new

- **Live TV:** current EPG name and broadcast hours in IINA and macOS Now Playing. An expired IPTVnator Remote EPG entry is automatically replaced using read-only XMLTV or the configured provider's cached programme schedule, even without clicking IPTVnator.
- **Catch-up:** detects REST and legacy Xtream timeshift streams, keeps the selected archived programme, and displays its actual broadcast start/end when the provider supplies reliable clock and timezone data.
- **Artwork:** channel logo in Now Playing; opaque-black transparent PNG normalization, bounded in-memory logo cache, shorter retry and better handling of rapid channel changes.
- **Safety:** playback, PiP, VOD/Trakt/EP+ and the existing VLC → IINA launcher v1.1 remain unchanged. Companion only binds localhost and reads IPTVnator SQLite without writes.

## Install / upgrade

1. Download **IPTVnator-Live-Companion-0.1.2.iinaplgz** from the release assets.
2. Install or upgrade the Python companion from this repository using the steps in the [README](https://github.com/olivergiangvu/iina-iptvnator-live-companion).
3. In IINA → Settings → Plugins, install the release package. Only one Live Companion version should be enabled. Fully restart IINA.
4. Verify Live EPG rolls over without interacting with IPTVnator; test one archived Catch-up title and its scheduled hours.

The original wrapper is not overwritten. Existing beta users can switch their repository checkout to main and run the included companion upgrade script, then install the stable plugin file.

## Tested

GitHub Actions runs Python and JavaScript regressions (Live title rollover, Catch-up broadcast hours, logo retries, VOD isolation), packages the plugin and verifies the original VLC wrapper SHA256. Live EPG auto-refresh, Catch-up programme/title/broadcast time and Now Playing artwork were also confirmed on IINA 1.5.0/macOS.

## Known limitations

- Control Center refresh timing follows IINA's native Now Playing implementation. The optional experimental track-refresh feature remains OFF by default for PiP safety.
- HTTP 400/403/404 provider logo links may still be unavailable; no automatic cross-channel logo fallback.
- If the provider's historical EPG or timezone is absent/ambiguous, scheduled times remain blank rather than being invented.
- Single-Mac localhost deployment. Do not expose port 8766 to a LAN or upload raw credential-bearing IINA logs.

Source license: MIT. Read [SECURITY.md](https://github.com/olivergiangvu/iina-iptvnator-live-companion/blob/main/SECURITY.md) before exposing any external integration.
