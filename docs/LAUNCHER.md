# Playback launcher v1.1

[Home](../README.md) · [Installation](INSTALLATION.md) · [Operations](OPERATIONS.md)

`companion/iptvnator-iina-vlc` is the **standalone playback adapter** installed at `~/.local/bin/iptvnator-iina-vlc`. IPTVnator calls it through its VLC-style External Player setting; the script launches **native IINA** with equivalent mpv arguments. It is neither a macOS `.app` nor part of the IINA plugin ZIP.

## Behaviour and boundaries

- Accepts the stream URL and forwards supported User-Agent, Referer, HTTP headers, stream title and start position to IINA/mpv.
- Ignores unsupported VLC remote-control flags.
- Invokes `/Applications/IINA.app/Contents/MacOS/IINA`; IINA manages playback and PiP.
- Does **not** fetch EPG, call Xtream provider APIs, transcode video or manage VOD/Trakt/EP+.
- Logs only the presence/count of options to `~/Library/Logs/iptvnator-iina-vlc.log`, never their values or the stream URL.

## Install or verify

For a **Git checkout**, use the non-overwriting installer:

```bash
cd "$HOME/Developer/iina-iptvnator-live-companion"

# Existing installation: read-only verification
bash scripts/install-launcher.sh --check

# New Mac only: installs if absent; verifies if identical;
# refuses existing different files and symlinks
bash scripts/install-launcher.sh --install
```

The original v1.1 source has SHA-256:

```text
12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623
```

For a Release-asset installation, verify the downloaded file before installing it; see [Installation](INSTALLATION.md). Set IPTVnator's External Player executable to the **absolute path** of the launcher. Do not change a working external-player configuration during a metadata-only update.

## Versioning

**Launcher v1.1 is independently versioned** from IINA Plugin/Python Companion v0.1.2. The source file has remained byte-identical through the latter's Live/Catch-up changes. Every CI run checks the v1.1 SHA-256 and that the installer does not overwrite an existing custom executable.

The immutable `v0.1.2` Git tag contains the launcher source, but the helper `scripts/install-launcher.sh` was added to `main` **after** that tag. Do not check out the old tag expecting every later distribution helper to exist.

Security: the launcher necessarily passes the stream URL in IINA's process invocation. Other diagnostic tools may expose this URL; **never publish an unredacted `ps` output or IINA log**. The launcher's own log intentionally avoids secret values.
