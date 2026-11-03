# IPTVnator → IINA Live Companion

Bring **Live TV and Catch-up EPG** into IINA and macOS Now Playing: programme title, original broadcast hours and channel logo. Designed for **macOS / IINA 1.5.0 / IPTVnator Xtream**.

**Latest stable:** [v0.1.2](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.2) · [Changelog](CHANGELOG.md) · [MIT License](LICENSE)

## What it does

- **Live TV:** updates the current programme and local broadcast time automatically, including when IPTVnator's Remote API has stale EPG data.
- **Catch-up:** shows the selected *archived* programme and its original broadcast hours, rather than the current Live programme.
- **Now Playing:** adds the channel logo to IINA/macOS playback metadata, where IINA supports it.
- **No playback changes:** keeps IINA's native video, manual PiP and existing VOD/EP+/Trakt workflows.

## Three components, one repository

| Component | Version | Purpose |
| --- | --- | --- |
| [Playback launcher](docs/LAUNCHER.md) (`companion/iptvnator-iina-vlc`) | **v1.1** | Adapts IPTVnator's VLC external-player arguments to native IINA |
| [Python Metadata Companion](docs/METADATA_COMPANION.md) (`companion/server.py`) | **v0.1.2** | Read-only EPG/logo service on `127.0.0.1:8766`, managed by macOS LaunchAgent |
| [IINA plugin](Info.json) (`main.js`) | **v0.1.2** | Updates titles and attached-picture artwork in IINA |

Each installs separately. The IINA `.iinaplgz` package **does not** install the launcher or Python LaunchAgent.

## Requirements

- macOS with **IINA 1.5.0** at `/Applications/IINA.app`.
- **IPTVnator 0.25 nightly**, with an Xtream playlist, local SQLite database and Remote Control API enabled on `127.0.0.1:8765`.
- **Python 3.10+** (standard library only). No Docker or extra Python packages required.

## Quick start — new Git-based installation

Use a **permanent directory**. These installation commands are for a new setup; existing users should follow [Upgrade & operations](docs/OPERATIONS.md) instead.

```bash
git clone https://github.com/olivergiangvu/iina-iptvnator-live-companion.git \
  "$HOME/Developer/iina-iptvnator-live-companion"
cd "$HOME/Developer/iina-iptvnator-live-companion"

bash scripts/install-launcher.sh --install
./scripts/install-companion.sh
python3 scripts/package-plugin.py

curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
```

Then configure **IPTVnator → External Player (VLC)** to use the absolute path `~/.local/bin/iptvnator-iina-vlc`; install `dist/IPTVnator-Live-Companion-0.1.2.iinaplgz` in **IINA → Settings → Plugins** and restart IINA. The launcher installer refuses to overwrite an existing different file.

For a **download-only installation**, the [v0.1.2 GitHub Release](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.2) has three assets: the launcher, Python source archive (`.tar.gz`) and IINA plugin (`.iinaplgz`). See [Installation](docs/INSTALLATION.md) for both methods.

> **Existing installations:** do not reinstall the LaunchAgent or replace a working launcher. Update the Git checkout and run `./scripts/upgrade-companion.sh`. See [Upgrade & operations](docs/OPERATIONS.md).

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation](docs/INSTALLATION.md) | New Mac, Git or Release assets, IPTVnator/IINA setup |
| [Upgrade & operations](docs/OPERATIONS.md) | Updates, health checks, troubleshooting, rollback |
| [Launcher](docs/LAUNCHER.md) | v1.1 executable, integrity, external-player arguments |
| [Metadata Companion](docs/METADATA_COMPANION.md) | Python LaunchAgent lifecycle and storage |
| [Architecture](docs/ARCHITECTURE.md) | Live/Catch-up matching, data flow, scope |
| [Testing](docs/TESTING.md) | Automated tests and on-Mac acceptance checklist |
| [Security](SECURITY.md) | Localhost, credentials, safe issue reports |
| [Changelog](CHANGELOG.md) | Release history |

## Scope and limitations

EPG and artwork depend on what the Xtream provider supplies; missing or ambiguous times are **not invented**, and broken logo URLs may not have a fallback. macOS Control Center refresh timing belongs to IINA; the optional experimental track-refresh action is **off by default** for PiP safety.

The companion is a **single-Mac localhost service**, not a remotely exposed API. Keep Xtream stream URLs, database files and unredacted IINA logs out of public issues.
