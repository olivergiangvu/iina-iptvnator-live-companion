> **v0.1.2-rc.1 Catch-up test candidate (PR only; not released).** Restores IPTVnator Catch-up EPG title and channel artwork for both Xtream REST `/timeshift/...` and legacy `/streaming/timeshift.php` URL formats. Existing Live TV, VOD/EP+/Trakt, and wrapper v1.1 remain unchanged.
>
> **Test on Mac:** `cd ~/Developer/iina-iptvnator-live-companion && git fetch origin && git switch fix/catchup-metadata-v0.1.2 && python3 scripts/package-plugin.py && ./scripts/upgrade-companion.sh`. Replace only the IINA Live Companion plugin with `dist/IPTVnator-Live-Companion-0.1.2-rc.1.iinaplgz`, then restart IINA. To roll back: `git switch main && ./scripts/upgrade-companion.sh`, then reinstall the v0.1.1 plugin from the public release. **Do not re-run `publish-public.sh`.**

# IPTVnator Live Companion — v0.1.1 Public Beta

**One GitHub repository** containing all components:

1. **IINA plugin (`Info.json`, `main.js`)**: polls a localhost companion every 15 s; sets a *file-local* dynamic Now Playing title and adds the Live channel logo as an mpv `attached-picture` track. This is the same **native macOS Now Playing** mechanism demonstrated in Episode Info Plus, not a fabricated video overlay.
2. **Companion (`companion/server.py`)**: read-only HTTP service on **127.0.0.1:8766**; queries IPTVnator Remote Control at **127.0.0.1:8765** and the existing `~/.iptvnator/databases/iptvnator.db` (`content.poster_url`). Never stores Xtream credentials. Returns EPG fields and safely proxies the channel logo only; does not reveal source image URLs.
3. **Existing VLC → IINA launcher (`companion/iptvnator-iina-vlc`)**: exact v1.1 source snapshot, SHA-256 `12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623` — deliberately **unchanged**. Native IINA/mpv playback, manually controlled PiP, headers/user-agent/referrer, VOD and the installed Trakt/EP+ plugin all remain as before. The optional native artwork-track refresh requires on-Mac PiP validation.

> **Status:** Live EPG updates in the IINA window and native channel artwork were observed on macOS with IINA 1.5.0. Native macOS Control Center **title refresh** at a programme boundary remains unverified; PiP must be tested with experimental refresh enabled. This does not change EPG retention or Catch-up duration. Public beta — not a stable release.


## Upgrade from installed v0.1.0 — wrapper remains unchanged

**Keep the original `~/.local/bin/iptvnator-iina-vlc` v1.1 unchanged.** Quit IINA before installing the plugin update (save/close existing playback). Unzip the **entire** v0.1.1 source zip with overwrite into `~/Developer` (it replaces companion source files **not** the installed launcher), then:

```bash
cd ~/Developer/iina-iptvnator-live-companion
cmp ~/.local/bin/iptvnator-iina-vlc companion/iptvnator-iina-vlc && echo 'WRAPPER IDENTICAL'
./scripts/upgrade-companion.sh
curl -fsS 'http://127.0.0.1:8766/health' | python3 -m json.tool
```

In IINA → Settings → Plugins, uninstall/disable the **old** IPTVnator Live Companion v0.1.0, install `dist/IPTVnator-Live-Companion-0.1.1.iinaplgz`, and reopen IINA. Leave Episode Info+ and Trakt untouched. Confirm only **one** Live Companion plugin is enabled.

Check identity and EPG for a specific Live channel (example 72746 = US: UPTV). A title hint intentionally prevents accidental matching of numerically identical Xtream IDs from other playlists:

```bash
curl -fsSG 'http://127.0.0.1:8766/status' \
  --data-urlencode 'stream_id=72746' \
  --data-urlencode 'title_hint=US: UPTV' | python3 -m json.tool
```

Expected: `matched: true`; `source: remote` when IPTVnator actively reports the same channel, `source: sqlite` if it has moved elsewhere but a current EPG row exists, or `source: none` if no local programme is available. `hasLogo: true` means the logo URL exists — the downstream download can still fail for offline/private logo hosts.

**What changed in 0.1.1:**
- Plugin sends **launched channel title hint + Xtream stream ID**; no longer demands Remote API is still selecting that channel.
- Companion reads current programmes from local `epg_programs` in read-only mode when Remote API is reporting another channel. No EPG scraping or remote credentials.
- Pure Python PNG compositor converts transparent PNG logos to an opaque RGB square with **black backing**, with no Pillow/ImageMagick dependency.
- Better diagnostics, 10-second polling, health version and health-verified LaunchAgent restart.
- Optional native Control Center refresh via a controlled *attached-picture* track-list change, disabled by default for PiP safety.

**IINA macOS Now Playing experimental refresh:** IINA 1.5.0 observes `media-title` and updates its window title, but does not directly listen to that event for the macOS Control Center. Its `PlayerCore.trackListChanged()` does call `NowPlayingInfoManager.updateInfo(withTitle: true)`. The plugin therefore includes an **opt-in**, experimental plugin-menu action, `Experimental: refresh Control Center on EPG change`, which re-attaches **only its own** album-art track at a programme boundary to request that native refresh. This does not reopen the stream, but it is not yet verified with your IINA 1.5.0/PiP session. **Initially OFF** for playback safety. It requires an attached channel logo, and does not alter other video/audio/subtitle tracks intentionally. Test once across a boundary; disable immediately if PiP flickers or the main video changes. Native Control Center/lock-screen refresh is not guaranteed until a real Mac test.

## Requirements

- IINA 1.5.0, IPTVnator 0.25 nightly with Remote Control enabled on port 8765.
- Python 3 (present on the target Mac); standard library only.
- IPTVnator's local SQLite content catalog with the Live stream's `xtream_id`, `title` and `poster_url`.
- IPTVnator External VLC player already pointing at `~/.local/bin/iptvnator-iina-vlc` v1.1.

## Non-destructive installation (macOS)

1. Extract this source repository to a **permanent location**, e.g. `~/Developer/iina-iptvnator-live-companion`. Do not run LaunchAgent from Downloads if you intend to move or delete it.
2. Verify wrapper snapshot and the deployed script are identical, without changing either:

   ```bash
   cd ~/Developer/iina-iptvnator-live-companion
   cmp ~/.local/bin/iptvnator-iina-vlc companion/iptvnator-iina-vlc && echo 'Wrapper v1.1: IDENTICAL'
   ```

3. Install companion read-only service (creates a *new* LaunchAgent only):

   ```bash
   ./scripts/install-companion.sh
   curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
   ```

4. In **IINA → Settings → Plugins → Install from local package**, select `dist/IPTVnator-Live-Companion-0.1.1.iinaplgz`. Restart IINA (close active video first) to load the newly installed plugin.
5. Start a Live channel from IPTVnator in its usual external-player mode. The plugin will update its **mpv media title** every 10 s, and attempt to add the **channel's artwork** after it verifies the Xtream stream ID and channel name against the local SQLite catalog. Check macOS **Control Center → Now Playing**.
6. Test an EPG boundary (including two consecutive `Storage Wars` episodes) without changing channel; title contains the programme's local start/end time. Confirm picture/video and PiP keep playing continuously. Then test VOD with EP+ / Trakt to make sure the Live plugin does not interact.

You can disable title or poster functions independently under IINA's **Plugin** menu.

### Diagnostic (privacy-safe)

```bash
# 200 + matched=true only when the selected channel and stream ID match
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
# Substitute the selected channel's Xtream numeric stream ID:
curl -fsS 'http://127.0.0.1:8766/status?stream_id=47721' | python3 -m json.tool
```

The companion returns **no Xtream playback URL, usernames, passwords or image source URL**. The JSON includes a source diagnostic (`remote`/`sqlite`/`none`) without exposing credentials. Its LaunchAgent log is `~/Library/Logs/iptvnator-live-companion.log` (and logs no API URLs or stream tokens).

## Clean rollback

1. In IINA Settings → Plugins disable/uninstall **IPTVnator Live Companion** (not EP+).
2. Stop companion service: `./scripts/uninstall-companion.sh`.
3. Keep the original `~/.local/bin/iptvnator-iina-vlc` untouched; playback and manual PiP continue exactly as before.

## Test locally

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_plugin.cjs            # optional; Node.js only for test
python3 scripts/package-plugin.py    # regenerates dist/*.iinaplgz
```

## Official public GitHub release

Repository: **https://github.com/olivergiangvu/iina-iptvnator-live-companion**.

To initialize and publish a NEW GitHub repository from the source archive on the owner's Mac, install/authenticate GitHub CLI and run:

```bash
brew install gh           # only if missing
gh auth login             # only if not already authenticated
cd ~/Developer/iina-iptvnator-live-companion
./scripts/publish-public.sh
```

The script checks the wrapper SHA, runs tests, builds the IINA plugin, creates a **Public** repository, pushes `main` and tag `v0.1.1`, then attaches `.iinaplgz` to a GitHub **prerelease**. It refuses to overwrite a repo that already exists. Run once only.

Official release: **https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.1** (available after successful publishing).

Source license: **MIT**; see `LICENSE`. IINA update-check integration is not yet configured.

## Architecture, boundaries, caveats

```text
IPTVnator native Electron/SQLite                         IINA 1.5.0
  ├─ Xtream Live `content.poster_url` ─┐                ┌─ plugin/main.js
  ├─ Remote API :8765 EPG Now ───────┐ │                │  ├─ EPG title → file-local mpv media title
  └─ External Player VLC args ────┐  │ │                │  └─ Channel logo → video-add attached-picture
                                 ▼  ▼ ▼                │
          v1.1 wrapper (unchanged) ───► native IINA/mpv ◄┘
                         │          companion :8766 ▲
                         └───────────── (separate service)
```

- To avoid an unrelated media player receiving EPG metadata, the plugin verifies **Xtream stream ID plus initial channel title hint** against the local IPTVnator `content` catalog; remote selection is not required after initial playback. Ambiguous duplicate catalog records are rejected. Playlist identity is not yet verified; if different providers reuse the same stream ID and channel name, an incorrect association remains possible.
- The companion proxy rejects private/loopback artwork URLs and limits images to JPEG/PNG/WebP ≤4 MB. Some provider logos may be unavailable under this safety policy; title continues working. No access tokens are written into the plugin.
- The plugin does **not** alter native playback, stream URL, chapter/subtitle state, audio/video codec, PiP configuration, or VOD scrobbling.
- mpv **attached-picture** mirrors the tested EP+ mechanism; IINA decides final artwork cropping in macOS Now Playing. Updating `media-title` triggers IINA's window-title update; macOS Control Center refresh is managed by IINA's native code and may require a separate event. Plugin-only dynamic Control Center title is not yet guaranteed.
- Not a general Xtream EPG archival system. It mirrors current EPG data already available from IPTVnator, not historical EPG from Strand/Desktop Telly.

## References

- IINA plugin API: https://docs.iina.io/pages/dev-guide.html
- IINA plugin distribution: https://docs.iina.io/pages/creating-plugins
- mpv `video-add`/`attached-picture`: https://mpv.io/manual/stable/
- EP+ POC: https://github.com/olivergiangvu/iina-episode-info-plus/blob/fix/epplus-beta4-now-playing-poster/epplus-now-playing.js
- IPTVnator content schema: https://github.com/4gray/iptvnator/blob/7a390f4/libs/shared/database/src/lib/schema.ts
