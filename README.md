# IPTVnator Live Companion

**Stable release: v0.1.2** · IINA 1.5.0 · macOS · IPTVnator Xtream

Bring IPTVnator's Xtream **Live TV** and **Catch-up** metadata into IINA's window title and macOS **Now Playing**: channel logo, programme name and scheduled broadcast time, without replacing your existing player.

[Latest releases](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases) · [Release v0.1.2](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.2) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

## Features

- **Live:** programme titles include the EPG broadcast window (local time). The plugin checks the companion every **10 seconds**. When IPTVnator's Remote API reports an expired show, the companion independently checks its read-only XMLTV database and then the configured Xtream provider's cached schedule; a programme boundary no longer requires clicking IPTVnator.
- **Catch-up:** distinguishes REST `/timeshift/…` and legacy `/streaming/timeshift.php` streams. Uses the selected archive start time to retrieve the **historical programme** and its actual broadcast window, without substituting the currently airing Live show.
- **Artwork:** adds channel artwork as an mpv attached-picture track, normalizes transparent PNG logos onto a black background, caches successful logos in memory and retries transient failures.
- **Playback isolation:** no changes to the IPTVnator → VLC → IINA wrapper v1.1, playback/codec settings, PiP, or VOD/EP+/Trakt. The Live Companion does not handle ordinary movie/series streams.
- **Privacy:** source URLs and Xtream credentials never go to the plugin API, Now Playing titles, or plugin logs. Companion binds only to localhost; SQLite remains read-only.

> macOS Control Center refresh is managed by IINA itself. Playback and metadata are tested with IINA 1.5.0, but Control Center timing may vary. The optional **Experimental: refresh Control Center on EPG change** switch is OFF by default; test it carefully with PiP if enabled.

## Requirements

- IINA 1.5.0 and IPTVnator 0.25 nightly (Xtream playlist).
- Existing working external-player path from IPTVnator through the user's VLC → IINA wrapper v1.1.
- Python **3.10+** and the Python standard library. No Docker, Pillow, FFmpeg, or additional Python packages are required.
- IPTVnator local database at `~/.iptvnator/databases/iptvnator.db` and its Remote Control API on `127.0.0.1:8765`.
- The Companion listens only at `127.0.0.1:8766`.

## Install (new deployment)

Clone or extract this repository into a **permanent** directory:

```bash
git clone https://github.com/olivergiangvu/iina-iptvnator-live-companion.git "$HOME/Developer/iina-iptvnator-live-companion"
cd "$HOME/Developer/iina-iptvnator-live-companion"
git checkout v0.1.2
python3 --version
python3 scripts/package-plugin.py
./scripts/install-companion.sh
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
```

In **IINA → Settings → Plugins**, install `dist/IPTVnator-Live-Companion-0.1.2.iinaplgz` and restart IINA. Enable only one version of this plugin. Configure IPTVnator's external player separately; **do not replace an existing working wrapper** during the metadata installation.

Alternatively, download the signed-by-GitHub-source release package `.iinaplgz` from [v0.1.2](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.2), but the companion still needs to be installed from the source repository.

## Upgrade from v0.1.1 / RC builds

Keep the wrapper and IPTVnator database untouched. Quit IINA before changing its plugin:

```bash
cd "$HOME/Developer/iina-iptvnator-live-companion"
git fetch origin
git switch main
git pull --ff-only
cmp "$HOME/.local/bin/iptvnator-iina-vlc" companion/iptvnator-iina-vlc && echo 'WRAPPER IDENTICAL'
./scripts/upgrade-companion.sh
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
python3 scripts/package-plugin.py
open -R "$PWD/dist/IPTVnator-Live-Companion-0.1.2.iinaplgz"
```

Expected health response: `{"ok": true, "dbExists": true, "version": "0.1.2"}`. In IINA Settings → Plugins, replace the previous Live Companion with `v0.1.2` and fully restart IINA. **Do not** re-run `scripts/publish-public.sh` on an existing repository.

## Quick smoke test

Play Live TV in IINA. Within a few polling cycles, the IINA title should contain the current programme and scheduled local window; channel artwork should appear in Now Playing if the provider's logo URL is reachable. Keep a Live channel running through its EPG boundary **without clicking IPTVnator**; the title should advance to the next show. Next open a past programme using IPTVnator Catch-up; its original name and scheduled time should remain fixed during playback. Test VOD and PiP separately.

For `US: MeTV Toons` (example Xtream stream ID `11590`), a privacy-safe status query is:

```bash
curl -fsSG 'http://127.0.0.1:8766/status' \
  --data-urlencode 'stream_id=11590' \
  --data-urlencode 'playback=live' \
  --data-urlencode 'title_hint=US: MeTV Toons' \
  | python3 -m json.tool
```

For archived metadata, use `playback=catchup` and the programme's **actual provider-clock** `archive_start=YYYY-MM-DD:HH-MM`. Timezone conversion uses the provider timezone when known; a missing/ambiguous guide leaves the broadcast window blank instead of inventing times.

## Architecture and safety

```text
IPTVnator (Xtream playlist, EPG, SQLite)
    │
    ├── Existing external VLC → IINA launcher v1.1 ──► IINA / mpv ─► Now Playing
    │                                                      ▲
    ├── Remote API :8765 ─┐                                │
    └── read-only SQLite ─┼──► Python Companion :8766 ◄── IINA Live Companion plugin
                          │
     Configured provider EPG ──► (server-side only, cached; no credentials in response)
```

The unchanged v1.1 wrapper has SHA-256 `12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623`. To match channels safely, the companion requires an Xtream numeric stream ID plus the launched channel title; ambiguous matches are rejected. A provider logo URL may exist in the database but return HTTP 400/403/404; the plugin does not modify IPTVnator metadata or silently substitute a logo from another stream.

Provider EPG and artwork availability are not guaranteed. Do not expose ports 8765/8766 beyond localhost or upload raw IINA logs containing credentials, stream URLs or OAuth tokens. See [Security](SECURITY.md) and [Architecture](docs/ARCHITECTURE.md).

## Development and testing

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_plugin.cjs
node tests/test_catchup.cjs
node tests/test_archive_plugin.cjs
node tests/test_latency.cjs
python3 scripts/package-plugin.py
```

Node.js is needed only for developer JavaScript tests, not for using the plugin. GitHub Actions runs the Python/JavaScript suite, validates the plugin archive, and checks the unchanged wrapper hash.

**Rollback:** Disable/uninstall only the IPTVnator Live Companion plugin in IINA, then restore the [v0.1.1 plugin release](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.1) if needed. Keep the original wrapper untouched. If reverting companion code, switch the local checkout to the corresponding version and run `./scripts/upgrade-companion.sh` from that checkout.

## License

MIT — see [LICENSE](LICENSE).
