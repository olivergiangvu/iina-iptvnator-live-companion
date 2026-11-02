#!/bin/bash
# Installs ONLY the read-only localhost companion service. Never touches wrapper/IINA plugin.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(command -v python3 || true)"
if [[ -z "$PYTHON" ]]; then echo 'python3 not installed' >&2; exit 1; fi
if [[ ! -f "$HOME/.iptvnator/databases/iptvnator.db" ]]; then
  echo 'IPTVnator database not found (expected ~/.iptvnator/databases/iptvnator.db).' >&2
  exit 1
fi
AGENTS="$HOME/Library/LaunchAgents"
LOGS="$HOME/Library/Logs"
LABEL="io.github.olivergiangvu.iptvnator-live-companion"
PLIST="$AGENTS/$LABEL.plist"
mkdir -p "$AGENTS" "$LOGS"
if [[ -e "$PLIST" ]]; then
  echo "Already installed: $PLIST" >&2
  echo 'To reinstall: launchctl bootout gui/$(id -u) "$PLIST"; rm "$PLIST"' >&2
  exit 1
fi
# Safe XML encoding for paths with special characters.
export LIVE_COMPANION_PYTHON="$PYTHON" LIVE_COMPANION_SCRIPT="$ROOT/companion/server.py" LIVE_COMPANION_LABEL="$LABEL" LIVE_COMPANION_LOG="$LOGS/iptvnator-live-companion.log"
python3 - "$PLIST" <<'PY'
import os,plistlib,sys
p={"Label":os.environ["LIVE_COMPANION_LABEL"],"ProgramArguments":[os.environ["LIVE_COMPANION_PYTHON"],"-u",os.environ["LIVE_COMPANION_SCRIPT"]],"RunAtLoad":True,"KeepAlive":True,"StandardOutPath":os.environ["LIVE_COMPANION_LOG"],"StandardErrorPath":os.environ["LIVE_COMPANION_LOG"],"ProcessType":"Background"}
with open(sys.argv[1],"wb") as f: plistlib.dump(p,f)
PY
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed companion service on localhost:8766. Existing wrapper remains untouched."
echo "Health: curl -fsS http://127.0.0.1:8766/health"
