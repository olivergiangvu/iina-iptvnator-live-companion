# IPTVnator → IINA Launcher v1.1

**First-class companion component of this repository.**

This file is the actual standalone macOS shell launcher used at
`~/.local/bin/iptvnator-iina-vlc`. It is **not** a macOS `.app` bundle and is
**not** embedded inside the `.iinaplgz` plugin archive.

## The three pieces

| Piece | Source file | Installs to / purpose |
| --- | --- | --- |
| **Playback launcher v1.1** | [`companion/iptvnator-iina-vlc`](../companion/iptvnator-iina-vlc) | `~/.local/bin/iptvnator-iina-vlc`; converts IPTVnator's VLC external-player arguments to native IINA/mpv arguments |
| **Metadata companion v0.1.2** | [`companion/server.py`](../companion/server.py), [`companion/catchup.py`](../companion/catchup.py) | Read-only Python LaunchAgent on `127.0.0.1:8766`; EPG and logos |
| **IINA Live Companion plugin v0.1.2** | [`Info.json`](../Info.json), [`main.js`](../main.js) | `.iinaplgz` in IINA Settings → Plugins; native Now Playing title and artwork |

The launcher is **part of the repository's source** and remains exactly the
byte-verified **v1.1**. It is intentionally versioned separately from the
IINA plugin and Python metadata service.

## Installation / inspection

For an existing user, check without modifying anything:

```bash
cd "$HOME/Developer/iina-iptvnator-live-companion"
bash scripts/install-launcher.sh --check
cmp "$HOME/.local/bin/iptvnator-iina-vlc" companion/iptvnator-iina-vlc &&
  echo 'LAUNCHER IDENTICAL'
```

On a **new Mac** where the destination does not exist:

```bash
cd "$HOME/Developer/iina-iptvnator-live-companion"
bash scripts/install-launcher.sh --install
```

The script verifies the tracked launcher SHA-256 and writes only the missing
`~/.local/bin/iptvnator-iina-vlc` file, with executable permissions. It **refuses
to overwrite any existing different launcher** (including a symlink) and
does not modify IPTVnator's SQLite database, the companion LaunchAgent, IINA,
PiP, or any player preferences.

Configure IPTVnator's **External Player: VLC** option to call the absolute
launcher path. IPTVnator can continue using its existing VLC-style external
player arguments while the launcher invokes IINA directly.

## Playback behavior

- Preserves the original URL, User-Agent, Referer, and HTTP header values when
  forwarding VLC-style external player inputs to native IINA/mpv.
- Sends channel title using `--mpv-force-media-title` so the Live plugin can
  identify the channel; also accepts the optional start position.
- Silently ignores known VLC remote control flags unsupported by IINA.
- Calls the native IINA binary at
  `/Applications/IINA.app/Contents/MacOS/IINA`.
- **Does not** auto-enter PiP, transcode, replace the codec, fetch EPG,
  query provider APIs, or manage VOD/Trakt/EP+.

The log at `~/Library/Logs/iptvnator-iina-vlc.log` records **only option flags
and counts**; never share full `ps` command lines or IINA logs as these may
contain credential-bearing stream URLs or unrelated OAuth tokens.

## Source integrity

The committed launcher v1.1 SHA-256:

```text
12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623
```

The repository's GitHub Actions workflow checks this hash and exercises the
installer's non-overwriting behavior. **Future launcher changes require their
own version and explicit user consent**; metadata plugin upgrades must never
silently replace the playback launcher.

## Why this is not part of the IINA plugin ZIP

IINA's `.iinaplgz` plugin format installs the JavaScript plugin, not a shell
executable under `~/.local/bin` or a macOS LaunchAgent. This repository
therefore ships **all three components together as source** and documents
their separate installation stages. The stable `v0.1.2` source tag already
contains the original launcher source; the helper installer added later on
`main` does not alter the released tag or executable.
