#!/bin/bash
# Restart only the existing live companion LaunchAgent; never replaces VLC adapter.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="io.github.olivergiangvu.iptvnator-live-companion"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
if [[ ! -f "$PLIST" ]]; then
  echo "Existing LaunchAgent not found; use scripts/install-companion.sh" >&2
  exit 1
fi
export EXPECTED_SCRIPT="$ROOT/companion/server.py"
python3 - "$PLIST" <<'PY'
import os,plistlib,sys
with open(sys.argv[1],'rb') as f: p=plistlib.load(f)
assert os.environ['EXPECTED_SCRIPT'] in p.get('ProgramArguments',[]), (
    'LaunchAgent runs a different script path. Do not restart an unknown service.'
)
PY
python3 -m py_compile "$EXPECTED_SCRIPT" "$ROOT/companion/logo.py" "$ROOT/companion/catchup.py"
launchctl kickstart -k "gui/$(id -u)/$LABEL"
for ((i=0;i<20;i++)); do
  if curl --connect-timeout 1 --max-time 2 -fsS 'http://127.0.0.1:8766/health' \
    | python3 -c 'import json,sys; d=json.load(sys.stdin);sys.exit(0 if d.get("ok") and d.get("dbExists") and d.get("version")=="0.1.2-rc.6" else 1)' 2>/dev/null; then
    echo "Companion v0.1.2-rc.6 ACTIVE on 127.0.0.1:8766 (wrapper unchanged)."
    exit 0
  fi
  sleep 0.5
done
echo 'Companion failed health verification. See ~/Library/Logs/iptvnator-live-companion.log' >&2
exit 1
