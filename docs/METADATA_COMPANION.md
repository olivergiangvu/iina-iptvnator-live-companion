# Python Metadata Companion v0.1.2

[Home](../README.md) · [Installation](INSTALLATION.md) · [Operations](OPERATIONS.md) · [Architecture](ARCHITECTURE.md)

A small Python service running as a **macOS user LaunchAgent**. It reads IPTVnator's SQLite catalog and EPG **read-only**, checks the Remote API and, when needed, queries the user's configured Xtream provider for programme data. It provides EPG/title and logo metadata to the IINA plugin; it does **not** control video playback.

## Runtime

| Resource | Location |
| --- | --- |
| Service code | `companion/server.py`, `companion/catchup.py`, `companion/logo.py` |
| LaunchAgent | `~/Library/LaunchAgents/io.github.olivergiangvu.iptvnator-live-companion.plist` |
| API | `127.0.0.1:8766` (`/health`, `/status`, `/logo`) |
| IPTVnator Remote API | `127.0.0.1:8765` |
| IPTVnator database | `~/.iptvnator/databases/iptvnator.db` |
| Local log | `~/Library/Logs/iptvnator-live-companion.log` |

Requires Python **3.10+**, standard library only. The LaunchAgent runs with `RunAtLoad` and `KeepAlive` under the current user account. No root privileges, Docker container or background auto-updater are installed.

## Deployment lifecycle

- **First installation:** `./scripts/install-companion.sh` creates and registers the LaunchAgent. It refuses to replace an existing plist.
- **Upgrade:** update the *existing* source directory, then run `./scripts/upgrade-companion.sh`. It validates the plist's script path, compiles the Python sources, restarts the LaunchAgent and checks the expected `/health` version.
- **Removal:** `./scripts/uninstall-companion.sh` removes only the LaunchAgent, leaving the database, launcher and IINA plugin untouched.

The plist contains an **absolute server path**. Keep the directory permanent; extracting a new copy elsewhere will **not** update the active service. Existing installations in `~/Developer` should stay there; new archive-based installations may use `~/Library/Application Support/IPTVnator Metadata Companion`.

For precise commands covering Git and the standalone Release archive, use [Installation](INSTALLATION.md) and [Operations](OPERATIONS.md). Do not run a second service or reinstall the LaunchAgent on a working setup.

## What the API returns

- `/health`: status, database presence and Companion version.
- `/status`: matched channel, EPG programme/title, real broadcast start/end when known, source indicator and logo availability.
- `/logo`: validated/normalized image bytes, or an error if the provider logo is unavailable.

For **Live**, the service verifies that Remote EPG times are current; it falls back to read-only local XMLTV, then the configured provider's cached schedule. For **Catch-up**, it resolves the selected archived programme using stream ID, channel name and archive start time. Both use bounded network requests and caches.

Xtream credentials can be read from the existing IPTVnator catalog to query the configured provider, but the service does **not** return those credentials or stream URLs in its API. See [Security](../SECURITY.md).

## Support limits

- A stale or missing provider programme schedule cannot be fabricated.
- Invalid/unreachable/private logo URLs are not replaced with guesses from other channels.
- The API is bound to **localhost**, intended for a single user on one Mac; do not expose it via a proxy, tunnel or LAN bind.
- Updates are **manual and explicit**, even when GitHub publishes a newer release.
