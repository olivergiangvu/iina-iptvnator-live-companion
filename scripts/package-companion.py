#!/usr/bin/env python3
"""Build the self-contained source distribution for macOS Metadata Companion.

No credentials, IPTVnator database, launcher, plugin, caches or user files are
packaged. The source tree has the same relative layout expected by its
install/upgrade/uninstall LaunchAgent scripts.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "Info.json").read_text(encoding="utf-8"))["version"]
PACKAGE = f"IPTVnator-Metadata-Companion-{VERSION}"
FILES = (
    "companion/server.py",
    "companion/logo.py",
    "companion/catchup.py",
    "scripts/install-companion.sh",
    "scripts/upgrade-companion.sh",
    "scripts/uninstall-companion.sh",
    "docs/METADATA_COMPANION.md",
)


def build() -> Path:
    target = ROOT / "dist" / (PACKAGE + ".tar.gz")
    target.parent.mkdir(parents=True, exist_ok=True)
    checksums = {}
    with target.open("wb") as out:
        with gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0) as compressed:
            with tarfile.open(mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT) as archive:
                for rel in FILES:
                    file = ROOT / rel
                    if not file.is_file() or file.is_symlink():
                        raise RuntimeError(f"Required source missing or symlinked: {rel}")
                    contents = file.read_bytes()
                    checksums[rel] = hashlib.sha256(contents).hexdigest()
                    info = tarfile.TarInfo(f"{PACKAGE}/{rel}")
                    info.size = len(contents)
                    info.mode = 0o755 if rel.startswith("scripts/") else 0o644
                    info.uid = 0
                    info.gid = 0
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(contents))
                manifest = json.dumps(
                    {"name": "IPTVnator Metadata Companion",
                     "version": VERSION,
                     "files_sha256": checksums},
                    indent=2, sort_keys=True,
                ).encode("utf-8") + b"\n"
                info = tarfile.TarInfo(f"{PACKAGE}/manifest.json")
                info.size = len(manifest)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(manifest))
    return target


if __name__ == "__main__":
    print(build())
