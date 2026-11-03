#!/usr/bin/env bash
# Safe installer/checker for the standalone IPTVnator VLC -> IINA launcher.
# Source is companion/iptvnator-iina-vlc v1.1 (SHA-256 locked).
# This script NEVER overwrites a user's existing launcher.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/companion/iptvnator-iina-vlc"
TARGET="$HOME/.local/bin/iptvnator-iina-vlc"
EXPECTED='12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623'
MODE="${1:---check}"

if [[ "$#" -ne 0 && "$#" -ne 1 ]] || [[ "$MODE" != "--check" && "$MODE" != "--install" ]]; then
  echo "Usage: $0 [--check|--install]" >&2
  echo "Default --check is read-only; --install copies ONLY if the destination is absent." >&2
  exit 64
fi

if [[ ! -f "$SOURCE" ]]; then
  echo "Launcher source is missing from repository." >&2
  exit 1
fi

ACTUAL="$(shasum -a 256 "$SOURCE" | awk '{print $1}')"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "Launcher source SHA-256 differs from v1.1; refusing operation." >&2
  exit 1
fi

if [[ -L "$TARGET" ]]; then
  echo "Destination is a symbolic link; will not follow or replace: $TARGET" >&2
  exit 1
fi

if [[ -e "$TARGET" ]]; then
  if [[ -f "$TARGET" ]] && cmp -s "$SOURCE" "$TARGET"; then
    echo "LAUNCHER IDENTICAL (v1.1): $TARGET"
    if [[ ! -x "$TARGET" ]]; then
      echo "WARNING: existing launcher is not executable; not changing permissions automatically." >&2
      exit 1
    fi
    exit 0
  fi
  echo "Destination differs from the repository source. Refusing to overwrite: $TARGET" >&2
  echo "Back up and review the existing file manually before any replacement." >&2
  exit 1
fi

if [[ "$MODE" == "--check" ]]; then
  echo "NOT INSTALLED: $TARGET"
  echo "Run ./scripts/install-launcher.sh --install for a new deployment."
  exit 1
fi

mkdir -p "$HOME/.local/bin"
install -m 755 "$SOURCE" "$TARGET"
if ! cmp -s "$SOURCE" "$TARGET"; then
  echo "Installation verification failed." >&2
  exit 1
fi

echo "INSTALLED launcher v1.1: $TARGET"
echo "Configure IPTVnator External Player = VLC executable path:"
echo "  $TARGET"
echo "This does not modify IPTVnator, IINA, the companion service, or any existing launcher."
