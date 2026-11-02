#!/usr/bin/env python3
"""Create a valid root-Info.json IINA local-install package (no companion files)."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
root = Path(__file__).resolve().parent.parent
info = json.loads((root / "Info.json").read_text())
out = root / "dist" / f"IPTVnator-Live-Companion-{info['version']}.iinaplgz"
out.parent.mkdir(exist_ok=True)
with ZipFile(out, "w", ZIP_DEFLATED) as z:
    for name in ["Info.json", "main.js"]:
        z.write(root / name, arcname=name)
print(out)
