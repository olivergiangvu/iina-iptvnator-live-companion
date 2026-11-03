# Catch-up Fix v0.1.2-rc.5 — Test Plan

Unreleased candidate. Do not publish v0.1.2 until Mac testing passes.

1. `cd ~/Developer/iina-iptvnator-live-companion`
2. `git fetch origin && git switch fix/catchup-metadata-v0.1.2`
3. `python3 scripts/package-plugin.py && ./scripts/upgrade-companion.sh`
4. Check `curl -fsS http://127.0.0.1:8766/health` shows `0.1.2-rc.5`.
5. In IINA Settings → Plugins, install `dist/IPTVnator-Live-Companion-0.1.2-rc.5.iinaplgz` in place of Live Companion v0.1.1, restart IINA.
6. Open a Catch-up programme in IPTVnator. IINA should show `Channel · Archived Programme` plus a channel logo when supplied. It must not switch title to Live Now.
7. Switch to Live and verify EPG title changes as usual. Open VOD to confirm EP+/Trakt unaffected.

Rollback: `git switch main && ./scripts/upgrade-companion.sh` and reinstall previous Live Companion plugin v0.1.1.

Never share credential-bearing Xtream URLs; the companion API sends only numerical stream ID, launch title, and mode.


Additional RC3 check: IPTVnator opens archived channel with only `US: MeTV Toons` title. Expect `catchup-sqlite` or `catchup-provider` source and correct selected show after stream loads; a provider with no archived guide may still show channel-only metadata. Never upload raw IINA logs or provider URLs.


RC4 Live latency acceptance: open Live, confirm fast EPG title, logo and native Now Playing without repeated opens; switch channels quickly and verify latest channel wins; retain Catch-up name/logo. First logo fetch still depends on network.


RC5 clock-boundary verification: keep a Live channel playing through a programme end WITHOUT clicking/focusing IPTVnator. The IINA window title must move to the next show, and status `source` should be `sqlite` or `live-provider` if the Remote EPG is stale. Catch-up title/logo must remain pinned to the selected archived show. The macOS Now Playing title may need the separate experimental refresh option.
