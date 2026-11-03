"""Documentation integrity checks: local links, navigation, stale guides."""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = (
    "docs/INSTALLATION.md",
    "docs/OPERATIONS.md",
    "docs/LAUNCHER.md",
    "docs/METADATA_COMPANION.md",
    "docs/ARCHITECTURE.md",
    "docs/TESTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
)


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_links_exist(self):
        pattern = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")
        docs = (ROOT / "README.md", ROOT / "SECURITY.md",
                ROOT / "CHANGELOG.md", *(ROOT / "docs").glob("*.md"))
        for doc in docs:
            content = doc.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                destination = match.group(1).strip().split(" ", 1)[0]
                parsed = urlsplit(destination)
                if parsed.scheme or destination.startswith("//") or not parsed.path:
                    continue  # external URL or same-page anchor
                target_path = unquote(parsed.path)
                with self.subTest(document=str(doc.relative_to(ROOT)), link=destination):
                    target = (doc.parent / target_path).resolve()
                    self.assertTrue(target.is_relative_to(ROOT.resolve()),
                                    "Relative document link escapes repository")
                    self.assertTrue(target.is_file(),
                                    f"Missing linked file: {target_path}")

    def test_readme_has_clear_navigation(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for rel in GUIDES:
            with self.subTest(guide=rel):
                self.assertIn(f"]({rel})", readme)

    def test_old_catchup_specific_guide_is_retired(self):
        self.assertFalse((ROOT / "docs/CATCHUP_FIX_TEST.md").exists())


if __name__ == "__main__":
    unittest.main()
