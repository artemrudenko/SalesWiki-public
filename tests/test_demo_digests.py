"""Tests for scripts/generate_demo_digests.py - sample role digests from demo data."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "generate_demo_digests.py"


class TestGenerateDemoDigests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(prefix="demo-digests-")
        cls.out = Path(cls.tmp.name)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--output-root", str(cls.out)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def read(self, name: str) -> str:
        path = self.out / name
        self.assertTrue(path.exists(), f"missing digest: {name}")
        return path.read_text(encoding="utf-8")

    def test_ae_digest_has_leads_and_synthetic_banner(self) -> None:
        text = self.read("my-day-ae.md")
        self.assertIn("synthetic", text.lower())
        self.assertIn("Lead", text)
        self.assertIn("generate_demo_digests.py", text)

    def test_marketing_digest_exists_and_hides_deal_economics(self) -> None:
        text = self.read("my-day-marketing.md")
        self.assertIn("synthetic", text.lower())
        for secret in ("Discount floor", "ACV", "RivalCorp"):
            self.assertNotIn(secret, text)

    def test_hos_pipeline_digest_shows_risk(self) -> None:
        text = self.read("pipeline-digest-hos.md")
        self.assertIn("synthetic", text.lower())
        self.assertIn("risk", text.lower())

    def test_index_links_all_digests(self) -> None:
        text = self.read("index.md")
        for name in ("my-day-ae.md", "my-day-marketing.md", "pipeline-digest-hos.md"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
