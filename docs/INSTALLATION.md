# Installation

[Home](../README.md) · [Operations](OPERATIONS.md) · [Launcher](LAUNCHER.md) · [Metadata service](METADATA_COMPANION.md)

This integration has **three separately installed components**. Complete all three for Live and Catch-up metadata to work.

## Prerequisites

- macOS, IINA **1.5.0** installed in `/Applications/IINA.app`.
- IPTVnator **0.25 nightly**, with a working **Xtream** playlist and its Remote Control API enabled on `127.0.0.1:8765`.
- An existing IPTVnator SQLite database: `~/.iptvnator/databases/iptvnator.db`.
- Python **3.10+**, available as `python3`. Git is needed for Method A only.

Check prerequisites before installing:

```bash
python3 --version
test -x /Applications/IINA.app/Contents/MacOS/IINA && echo 'IINA found'
test -f "$HOME/.iptvnator/databases/iptvnator.db" && echo 'IPTVnator DB found'
curl -fsS --max-time 3 'http://127.0.0.1:8765/api/remote-control/status' \
  >/dev/null && echo 'IPTVnator Remote API available'
```

**Do not proceed with a second installation** if a working Companion already occupies port 8766. Use [Operations](OPERATIONS.md) to update it.

## Method A — Git checkout (recommended)

Clone into a **permanent folder**; do not install from temporary Downloads.

```bash
git clone https://github.com/olivergiangvu/iina-iptvnator-live-companion.git \
  "$HOME/Developer/iina-iptvnator-live-companion"
cd "$HOME/Developer/iina-iptvnator-live-companion"
```

Install each part:

```bash
# 1. Playback launcher v1.1 — never overwrites a different existing file
bash scripts/install-launcher.sh --install

# 2. Python Metadata Companion — registers LaunchAgent only once
./scripts/install-companion.sh

# 3. Build local IINA plugin package
python3 scripts/package-plugin.py
```

Use the **current `main` checkout** for these installation helpers. The immutable `v0.1.2` Git tag predates the later launcher/metadata distribution scripts, even though the runtime code remains v0.1.2. For runtime version pinning use the official Release downloads or keep a tested commit SHA.

Finish configuration:

1. In **IPTVnator → External Player**, select its VLC-style external-player option and set the **executable** to the full path, e.g. `/Users/yourname/.local/bin/iptvnator-iina-vlc`. It is a shell script that opens **IINA**, not VLC.
2. In **IINA → Settings → Plugins**, install `dist/IPTVnator-Live-Companion-0.1.2.iinaplgz` and restart IINA. Enable **one** Live Companion instance only.
3. Open a Live channel through IPTVnator and confirm IINA playback, EPG title and logo. Then test a programme using Catch-up.

Validate the Python service:

```bash
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
```

Expected: `"ok": true`, `"dbExists": true` and `"version": "0.1.2"`.

## Method B — GitHub Release assets (without Git)

The [v0.1.2 Release](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.2) provides:

| File | Purpose |
| --- | --- |
| `iptvnator-iina-vlc` | Original standalone launcher v1.1 |
| `IPTVnator-Metadata-Companion-0.1.2.tar.gz` | Python service, LaunchAgent scripts and checksum manifest |
| `IPTVnator-Live-Companion-0.1.2.iinaplgz` | IINA JavaScript plugin |

Download these files from the **official release** to `~/Downloads`.

**Launcher:** for a *new* installation only, verify its original SHA-256 before copying. If there is already a launcher, do not overwrite it.

```bash
shasum -a 256 "$HOME/Downloads/iptvnator-iina-vlc"
# Expected:
# 12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623
```

Install it with an explicit non-overwrite guard (the `main` checkout's
`install-launcher.sh` provides the same protection):

```bash
TARGET="$HOME/.local/bin/iptvnator-iina-vlc"
if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  echo "Existing launcher detected; leaving it unchanged: $TARGET"
else
  mkdir -p "$HOME/.local/bin"
  install -m 755 "$HOME/Downloads/iptvnator-iina-vlc" "$TARGET"
fi
```

**Metadata Companion:** extract the archive to a permanent directory:

```bash
ROOT="$HOME/Library/Application Support/IPTVnator Metadata Companion"
mkdir -p "$ROOT"
tar -xzf "$HOME/Downloads/IPTVnator-Metadata-Companion-0.1.2.tar.gz" \
  -C "$ROOT" --strip-components=1
cd "$ROOT"
./scripts/install-companion.sh
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
```

**IINA plugin:** install the downloaded `.iinaplgz` via IINA Settings → Plugins, then restart IINA. Point IPTVnator at the installed launcher as described above.

> Method A and Method B use **different source paths** for the LaunchAgent. Choose **one** method per Mac; don't install both. The LaunchAgent records its Python source path and will not automatically switch between them.

## What stays separate

- The launcher is a standalone executable under `~/.local/bin`.
- The Python service is a user LaunchAgent plus source files; it needs no root privileges.
- The IINA plugin is installed through IINA. Its package cannot deploy the other two components.
- Neither installer modifies the IPTVnator SQLite database or existing streaming configuration.

For upgrades, diagnostic commands and rollback, follow [Operations](OPERATIONS.md). For source checksums and launcher behaviour, see [Launcher](LAUNCHER.md).
