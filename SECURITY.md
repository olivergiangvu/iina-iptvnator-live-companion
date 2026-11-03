# Security and privacy

[Home](README.md) · [Architecture](docs/ARCHITECTURE.md) · [Operations](docs/OPERATIONS.md)

This project is intended for **one macOS user on a trusted local machine**, not as a network-exposed service.

## Data access and network boundaries

- Python Metadata Companion binds to `127.0.0.1:8766`; IPTVnator Remote Control is expected at `127.0.0.1:8765`. **Never forward either port** over your LAN, VPN tunnel, Docker proxy or the public internet.
- The companion opens `~/.iptvnator/databases/iptvnator.db` in **read-only mode**. It never modifies your playlists or EPG tables.
- When local guide data is insufficient, the Python process may read configured Xtream credentials from the database and request the relevant programme guide **from that provider**. Credentials and media URLs are not returned by our localhost API or intentionally written to the Companion's log.
- The launcher necessarily passes the stream URL and playback headers to native IINA/mpv. Other process inspectors or third-party plugins could expose them; treat their diagnostics as sensitive.
- The image proxy limits downloads and rejects private-address image hosts, but provider-controlled content remains untrusted. This is **not** a security-hardened multi-user image service.

## Safe issue reports

**Do not publish** database copies, Xtream hostnames with credentials, full playback URLs, API queries containing secrets, access tokens, cookies, unredacted `ps` output or raw IINA logs. Unrelated plugins can also place OAuth tokens in the same logs.

Share only the version, a **sanitized** `/health` response, mode (Live/Catch-up), and minimal relevant log lines after removing secrets. If credentials were posted publicly, rotate or revoke them with their provider.

## Installation and maintenance

- The standalone launcher installer verifies the pinned v1.1 checksum and **refuses to overwrite** an existing different executable or symlink.
- The Companion installer creates a per-user LaunchAgent once; the upgrade script verifies the expected script path and health version before reporting success.
- Source upgrades and IINA plugin replacements are **manual**, with no silent background updater.
- Do not run install scripts from an untrusted fork or change the service bind address.

For a suspected security issue, contact the repository maintainer privately rather than posting credentials or vulnerability details in a public issue.
