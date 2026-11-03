#!/usr/bin/env bash
# Test the optional launcher installer without touching real user files.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOL="$ROOT/scripts/install-launcher.sh"
SOURCE="$ROOT/companion/iptvnator-iina-vlc"

bash -n "$TOOL"
bash -n "$SOURCE"

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
USER_HOME="$SANDBOX/home"
mkdir -p "$USER_HOME"
DST="$USER_HOME/.local/bin/iptvnator-iina-vlc"

if HOME="$USER_HOME" bash "$TOOL" --check > /dev/null 2>&1; then
  echo "Expected --check to report absent launcher" >&2
  exit 1
fi
HOME="$USER_HOME" bash "$TOOL" --install > /dev/null
HOME="$USER_HOME" bash "$TOOL" --check > /dev/null
cmp "$SOURCE" "$DST"
test -x "$DST"
HOME="$USER_HOME" bash "$TOOL" --install > /dev/null

# An existing different launcher must never be silently replaced.
printf '\n# local customization\n' >> "$DST"
cp "$DST" "$SANDBOX/modified"
if HOME="$USER_HOME" bash "$TOOL" --install > /dev/null 2>&1; then
  echo "Installer overwrote the user's modified launcher" >&2
  exit 1
fi
cmp "$DST" "$SANDBOX/modified"

# Refuse symlinks even if they point to an identical executable.
rm "$DST"
ln -s "$SOURCE" "$DST"
if HOME="$USER_HOME" bash "$TOOL" --install > /dev/null 2>&1; then
  echo "Installer accepted existing symlink" >&2
  exit 1
fi

echo "PASS: standalone launcher v1.1 installs from repository, is executable, and never overwrites existing files"
