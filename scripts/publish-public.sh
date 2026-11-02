#!/usr/bin/env bash
# Run on the owner's macOS workstation after `gh auth login`.
# Create one NEW PUBLIC GitHub repository, push source, tag, and upload plugin.
set -euo pipefail

REPO='olivergiangvu/iina-iptvnator-live-companion'
TAG='v0.1.1'
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

for cmd in git gh python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    if [[ "$cmd" == gh ]]; then echo 'Install: brew install gh; then gh auth login' >&2; fi
    exit 1
  fi
done

if ! gh auth status >/dev/null 2>&1; then
  echo 'GitHub CLI is not authenticated: run gh auth login' >&2
  exit 1
fi
USER="$(gh api user --jq .login)"
if [[ "$USER" != 'olivergiangvu' ]]; then
  echo "Expected GitHub account olivergiangvu; authenticated as $USER" >&2
  exit 1
fi
if gh repo view "$REPO" --json name >/dev/null 2>&1; then
  echo "Repository already exists: https://github.com/$REPO" >&2
  echo 'Refusing to overwrite an existing repository. Publish manually after inspection.' >&2
  exit 1
fi
if [[ -d .git ]]; then
  echo 'A Git repository already exists in this directory. Refusing automatic publication.' >&2
  exit 1
fi

ACTUAL="$(shasum -a 256 companion/iptvnator-iina-vlc | awk '{print $1}')"
EXPECTED='12d9be1a61f3aa8545de853df479c4c8d18979e2909b244f7248e1237550f623'
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo 'Wrapper checksum mismatch; refusing release.' >&2
  exit 1
fi
python3 -m unittest discover -s tests -p 'test_*.py' -v
if command -v node >/dev/null 2>&1; then
  node tests/test_plugin.cjs
else
  echo 'NOTE: Node.js not installed; plugin JavaScript tests were skipped.' >&2
fi
python3 scripts/package-plugin.py
ASSET="dist/IPTVnator-Live-Companion-0.1.1.iinaplgz"
python3 - "$ASSET" <<'PY'
import json, zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as z:
    assert set(z.namelist()) == {'Info.json', 'main.js'}
    assert json.loads(z.read('Info.json'))['version'] == '0.1.1'
print('Plugin package verified')
PY

if ! git var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
  echo 'Configure a local Git author first: git config --global user.name / user.email' >&2
  exit 1
fi

git init -q
git checkout -q -b main
git add -A
git commit -qm "Release $TAG: IINA Live Companion and unchanged VLC adapter"
git tag -a "$TAG" -m "First public beta $TAG"

gh repo create "$REPO" --public --source=. --remote=origin --push \
  --description 'IINA Live TV: IPTVnator dynamic EPG title and channel-logo Now Playing companion'
git push -q origin "$TAG"
gh release create "$TAG" "$ASSET" --repo "$REPO" --title "$TAG — First Public Beta" \
  --notes-file docs/RELEASE_NOTES_v0.1.1.md --prerelease

VISIBILITY="$(gh repo view "$REPO" --json visibility --jq .visibility)"
if [[ "$VISIBILITY" != 'PUBLIC' ]]; then
  echo "Repository created but visibility is $VISIBILITY, not PUBLIC!" >&2
  exit 1
fi
printf '\nPUBLISHED PUBLICLY:\n  https://github.com/%s\n  https://github.com/%s/releases/tag/%s\n' "$REPO" "$REPO" "$TAG"
