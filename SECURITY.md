# Security and privacy

The companion listens only on `127.0.0.1:8766`, and reads IPTVnator's existing
`127.0.0.1:8765` Remote Control endpoint and local SQLite database. It does not
require, publish, or log Xtream usernames, passwords, or media URLs. It does not
write to the IPTVnator database or control playback.

Use the included LaunchAgent scripts on **your own** Mac only. Do not expose
ports 8765 or 8766 to the LAN/Internet through Docker, proxies, or tunnelling.
Do not add personal playlists, server URLs, access tokens, `.env`, databases,
logs, or screenshots with personal data to issues or pull requests.

The logo downloader limits image size and blocks obviously private addresses,
but fetching arbitrary provider-supplied imagery still carries the risks
associated with untrusted external servers. Do not assume it is a hardened
multi-user service.

If you discover a security issue, contact the repository owner privately;
do not publish credentials or exploitable private endpoint details in an issue.
