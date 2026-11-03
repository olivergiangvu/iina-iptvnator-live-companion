"""Verify official Metadata Companion archive layout and source integrity."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util

_spec = importlib.util.spec_from_file_location("package_companion", ROOT / "scripts/package-companion.py")
packager = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packager)


class CompanionDistributionTests(unittest.TestCase):
    def test_archive_includes_service_and_installer_only(self):
        path = packager.build()
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "IPTVnator-Metadata-Companion-0.1.2.tar.gz")
        prefix = "IPTVnator-Metadata-Companion-0.1.2/"
        with tarfile.open(path, mode="r:gz") as archive:
            expected = {prefix + rel for rel in packager.FILES}
            expected.add(prefix + "manifest.json")
            self.assertEqual(set(archive.getnames()), expected)
            manifest = json.load(archive.extractfile(prefix + "manifest.json"))
            self.assertEqual(manifest["version"], "0.1.2")
            for rel in packager.FILES:
                member = archive.getmember(prefix + rel)
                contents = archive.extractfile(member).read()
                self.assertEqual(contents, (ROOT / rel).read_bytes())
                self.assertEqual(
                    hashlib.sha256(contents).hexdigest(),
                    manifest["files_sha256"][rel],
                )
                self.assertFalse(member.issym())
                self.assertEqual(member.mode & 0o111, 0o111 if rel.startswith("scripts/") else 0)

    def test_archive_rebuild_is_reproducible(self):
        target = packager.build()
        first = hashlib.sha256(target.read_bytes()).hexdigest()
        second = hashlib.sha256(packager.build().read_bytes()).hexdigest()
        self.assertEqual(first, second)

    def test_bundled_launchagent_scripts_have_valid_bash_syntax(self):
        for rel in packager.FILES:
            if rel.endswith(".sh"):
                subprocess.run(["bash", "-n", str(ROOT / rel)], check=True)


if __name__ == "__main__":
    unittest.main()
