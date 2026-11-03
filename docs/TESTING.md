# Testing and release acceptance

[Home](../README.md) · [Installation](INSTALLATION.md) · [Operations](OPERATIONS.md)

## Automated tests

From the repository root, run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Node.js is needed for development tests, not to run the plugin
node tests/test_plugin.cjs
node tests/test_catchup.cjs
node tests/test_archive_plugin.cjs
node tests/test_latency.cjs

# Verify launcher v1.1 source and non-overwriting installer
bash tests/test_launcher.sh
shasum -a 256 companion/iptvnator-iina-vlc

# Verify both release package formats
python3 scripts/package-plugin.py
python3 scripts/package-companion.py
```

GitHub Actions runs these regressions and verifies the stable plugin archive, Python source archive and original launcher checksum. This suite cannot fully emulate IINA's native Now Playing/Control Center behaviour; macOS smoke tests are still required.

## Manual on-Mac checklist

Use a real Xtream playlist with a valid programme schedule. **Never commit or upload its URL or credentials.**

- [ ] **Live:** open a channel in IINA. The window title shows the current programme and its local broadcast hours.
- [ ] **EPG rollover:** leave Live TV playing across a scheduled programme boundary **without clicking IPTVnator**. The programme title advances automatically.
- [ ] **Channel switch:** quickly change between Live channels. The latest channel's title and logo win, not stale data from a previous request.
- [ ] **Catch-up REST/legacy:** open an archived programme and verify its **selected historical title** and original broadcast hours remain fixed while playback advances.
- [ ] **Logo/Now Playing:** verify channel artwork in macOS Now Playing where IINA supports it; test the cold and warm load paths.
- [ ] **VOD:** open a regular movie/series with existing EP+/Trakt integrations. Live Companion must not take over.
- [ ] **Playback/PiP:** ensure playback remains continuous and the plugin does not trigger PiP automatically.
- [ ] **Companion/launcher:** check `/health` reports the deployed version and the original launcher is unchanged.

The experimental native Control Center refresh option is **OFF** by default. If enabled for testing, check PiP behaviour and disable it if it causes flicker or interruption.

## Observed v0.1.2 acceptance

On macOS with IINA 1.5.0, the original v0.1.2 validation confirmed Live EPG can advance without UI interaction and Catch-up displays archived programme title, its broadcast time and channel artwork. Provider availability and native Control Center timing may vary for other installations.

## When reporting bugs

Provide the plugin/Companion version, Live versus Catch-up mode, sanitized channel/stream ID if appropriate, `/health` result, and a short **redacted** plugin diagnostic. Avoid raw logs, command lines, provider URLs, passwords, stream tokens and OAuth credentials. See [Security](../SECURITY.md).
