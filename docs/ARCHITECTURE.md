# Design notes / test gates

**Isolation and rollback:** Wrapper is exact v1.1, zero modifications. Companion is a separately installed LaunchAgent, with a separate plugin identity. No writes to IPTVnator database and no modifications to the IINA installation or EP+ plugin sources. A disabled companion yields static original title, never breaks video playback.

**EPG title:** `http://127.0.0.1:8765/api/remote-control/status` carries a new `epgStart` when a same-name episode boundary occurs. Plugin signature includes channel + EPG title + start + end; display title includes programme time to force media-title change for same-name repeats. All times shown in the Mac's local timezone.

**Artwork:** Query `content` (type `live`, stream `xtream_id`) and validate title against active remote status. Proxy image with no credentials exposed to plugin, download into IINA plugin `@tmp`, `mpv.command('video-add', [path, 'auto+attached-picture', title])`, preserve original `vid`; verify track is albumart. This mirrors EP+ experimental native Now Playing proof of concept.

**Expected v0.1 limitations:** no source provider ID mapping beyond stream_id + channelName; no dynamic programme poster (logo stays for channel); missing local SQLite `content` causes safe no-op; public logo only; image downloaded on first match; native Control Center/PiP behavior not testable outside macOS. MPV track changes during Live require on-device validation.

**Acceptance tests on real Mac:**
1. Current untouched wrapper SHA-256 matches source repo snapshot.
2. Companion health `dbExists=true`; `/status?stream_id=...` returns `matched=true`, `hasLogo=true` on current channel.
3. IINA PiP/video does not switch to still artwork after `video-add` (the plugin restores `vid` if necessary).
4. IINA native Now Playing displays *channel logo*; EP+ still displays VOD posters when VOD playback.
5. EPG boundary, including two sequential Storage Wars episodes, updates Now Playing title without restarting the stream.
6. Changing channels causes new matching logo/title; closing IINA or switching to VOD stops updates.
7. Disabling plugin or uninstalling companion causes normal native playback without modifications.
