# Release acceptance — v0.1.2 stable

User-confirmed on macOS (IINA 1.5.0) on 2026-11-03:

- Live TV: EPG title/logo appear; programme transitions without interacting with IPTVnator.
- Catch-up: selected historical programme name, actual broadcast start/end and channel artwork appear in native macOS Now Playing.
- The VLC → IINA wrapper v1.1 remains byte-identical.
- Python/Node tests and packaging are verified by GitHub Actions.

## Regression QA for future updates

1. Leave Live TV playing through a scheduled programme boundary without clicking IPTVnator.
2. Change Live channels rapidly, verifying correct EPG, identity and artwork.
3. Launch REST or legacy Catch-up; check the selected historical show and real local broadcast hours.
4. Open normal VOD with EP+ / Trakt and check Live Companion does not take over.
5. Verify native Now Playing and PiP; experimental Control Center refresh remains opt-in/off.
6. Confirm Companion /health version and wrapper hash.

Never upload raw IINA logs or credential-bearing Xtream URLs. Provider EPG and macOS Control Center refresh may vary.
