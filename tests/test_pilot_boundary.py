"""Tests for the pilot-data leak guard in scripts/health_check.py.

Real pilot data (`dataset: pilot`) must live outside this repository; the
health check fails if a pilot directory or pilot-marked card shows up inside.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import health_check as hc  # noqa: E402


PILOT_CARD = """---
type: company
entity_id: company_01HZX5R9T2KQJ8M3N4P5Q6R7S8
dataset: pilot
---

# Company - Real Customer
"""

CLEAN_CARD = """---
type: company
entity_id: demo-company-x
dataset: demo
---

# Company - X
"""


class TestPilotBoundary(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="pilot-boundary-")
        self.root = Path(self.tmp.name)
        self.original_root = hc.ROOT
        hc.ROOT = self.root

    def tearDown(self) -> None:
        hc.ROOT = self.original_root
        self.tmp.cleanup()

    def errors(self) -> list:
        findings: list = []
        hc.check_pilot_boundary(findings)
        return [f for f in findings if f.severity == "ERROR"]

    def test_clean_repo_has_no_findings(self) -> None:
        (self.root / "wiki").mkdir()
        (self.root / "wiki" / "card.md").write_text(CLEAN_CARD, encoding="utf-8")
        self.assertEqual(self.errors(), [])

    def test_pilot_directory_inside_repo_is_an_error(self) -> None:
        (self.root / "pilot").mkdir()
        errors = self.errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("pilot", errors[0].message.lower())

    def test_pilot_dataset_card_inside_repo_is_an_error(self) -> None:
        (self.root / "wiki").mkdir()
        (self.root / "wiki" / "real.md").write_text(PILOT_CARD, encoding="utf-8")
        errors = self.errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("dataset: pilot", errors[0].message)

    def test_ignored_dirs_are_skipped(self) -> None:
        hidden = self.root / ".venv" / "lib"
        hidden.mkdir(parents=True)
        (hidden / "vendored.md").write_text(PILOT_CARD, encoding="utf-8")
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main()
