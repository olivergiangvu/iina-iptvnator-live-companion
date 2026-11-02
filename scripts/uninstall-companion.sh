#!/bin/bash
# Stop and remove ONLY the companion launch agent, leave wrapper and IINA unaffected.
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/io.github.olivergiangvu.iptvnator-live-companion.plist"
if [[ -f "$PLIST" ]]; then
  launchctl bootout "gui/$(id -u)" "$PLIST" || true
  rm "$PLIST"
  echo 'Companion service uninstalled. IPTVnator VLC → IINA wrapper untouched.'
else
  echo 'Companion service not installed.'
fi
