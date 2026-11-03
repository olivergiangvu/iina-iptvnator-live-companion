# Upgrade, health checks and troubleshooting

[Home](../README.md) · [Installation](INSTALLATION.md) · [Testing](TESTING.md) · [Security](../SECURITY.md)

## Update policy

Updates are **manual and version-tested**. A new GitHub Release does **not** automatically update the running Mac.

- `install-companion.sh` registers a macOS LaunchAgent **once**.
- `git pull` (or extracting a new Release archive) changes source files **on disk**.
- `upgrade-companion.sh` restarts the *existing* service and checks `/health`. **It does not install, replace or upgrade the playback launcher or IINA plugin.**
- The IINA plugin must be updated separately in **IINA → Settings → Plugins**, only when its version changes.
- The launcher v1.1 is versioned independently and must never be overwritten silently.

## Upgrade a Git-based installation

Use this path for an existing checkout at `~/Developer/iina-iptvnator-live-companion`:

```bash
cd "$HOME/Developer/iina-iptvnator-live-companion"
git switch main
git pull --ff-only
bash scripts/install-launcher.sh --check
./scripts/upgrade-companion.sh
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
```

A successful health response should include the installed version and `"dbExists": true`. For stable v0.1.2, the health version is `0.1.2`. When the **plugin** changes, run `python3 scripts/package-plugin.py`, replace the installed plugin and fully restart IINA.

Do not use `scripts/publish-public.sh` to update an existing repository. That script is the historical one-time repo creator.

## Upgrade a Release-archive installation

The service's LaunchAgent points to the **original extraction directory**. Keep that path stable.

1. Save a backup of the current source directory.
2. Download and verify the intended stable archive.
3. Extract its contents over the same installation directory.
4. Run `./scripts/upgrade-companion.sh` from that directory and verify `/health`.

Example **for a future version** (replace the filename with the actual published archive):

```bash
ROOT="$HOME/Library/Application Support/IPTVnator Metadata Companion"
cp -R "$ROOT" "$ROOT.backup"
tar -xzf "$HOME/Downloads/IPTVnator-Metadata-Companion-X.Y.Z.tar.gz" \
  -C "$ROOT" --strip-components=1
cd "$ROOT"
./scripts/upgrade-companion.sh
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool
```

Do not create a second LaunchAgent or move the directory without explicitly migrating the plist.

## Check a running installation

```bash
# Companion version and database state
curl -fsS http://127.0.0.1:8766/health | python3 -m json.tool

# LaunchAgent process state
launchctl print "gui/$(id -u)/io.github.olivergiangvu.iptvnator-live-companion" \
  | grep -E 'state =|pid =|last exit code'

# Check the launcher without modifying it (Git checkout installation)
cd "$HOME/Developer/iina-iptvnator-live-companion"
bash scripts/install-launcher.sh --check
```

To see which Python script the LaunchAgent uses (without revealing stream URLs):

```bash
python3 - <<'PY'
from pathlib import Path
import plistlib
p = Path.home() / "Library/LaunchAgents/io.github.olivergiangvu.iptvnator-live-companion.plist"
with p.open("rb") as f:
    args = plistlib.load(f)["ProgramArguments"]
print("Python executable:", args[0])
print("Service source:", args[-1])
PY
```

## Common symptoms

| Symptom | Check first |
| --- | --- |
| `curl: (7)` immediately after restart | Can be transient while the service starts; verify the final `/health` result |
| `/health` unavailable after restart | `launchctl print`, script path in plist, then local log `~/Library/Logs/iptvnator-live-companion.log` |
| `dbExists: false` | IPTVnator database path, playlist initialization and permissions |
| Live EPG is stale | `/status` source; if Remote EPG is expired, local/provider schedule must have valid times to advance |
| Catch-up title has no broadcast hours | Provider may lack historical EPG end time or reliable timezone; do not infer it from stream playback position |
| EPG title is right but Control Center is stale | IINA's native Now Playing refresh is distinct from mpv title updates; experimental refresh is optional |
| Logo missing | Provider image URL may be broken/private, or IINA has not refreshed its artwork track |
| Installer refuses existing launcher | Deliberate safety guard; check it manually and never overwrite without review |

**Logs:** `~/Library/Logs/iptvnator-live-companion.log` and `~/Library/Logs/iptvnator-iina-vlc.log`. **Never upload raw IINA logs**, full stream URLs, provider API calls, auth tokens or cookies. Redact before reporting issues.

## Rollback

1. Quit IINA and record the currently working version.
2. Restore the previous known-good Python source **at the same path**, then run its `upgrade-companion.sh` to restart the existing LaunchAgent.
3. If the IINA plugin was changed, reinstall the corresponding older `.iinaplgz` from its GitHub Release.
4. Leave `~/.local/bin/iptvnator-iina-vlc` untouched; it is independently versioned.

For Git checkouts, a known-good release tag or commit can be checked out in the **same folder**, provided the LaunchAgent still points there. Do not force-reset uncommitted work. The original [v0.1.1 beta](https://github.com/olivergiangvu/iina-iptvnator-live-companion/releases/tag/v0.1.1) is preserved as a rollback reference, but Live/Catch-up feature compatibility depends on using matched plugin and service versions.

## Remove the Python service

Run `./scripts/uninstall-companion.sh` from the active source directory. This removes **only** the LaunchAgent; it does not delete source files, the playback launcher, IPTVnator or the IINA plugin.
