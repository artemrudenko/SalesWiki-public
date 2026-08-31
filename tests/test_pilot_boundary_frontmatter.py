"""The pilot-boundary guard must not be bypassed by encoding (security review #7-low).

health_check.frontmatter only recognized frontmatter beginning with the exact
bytes '---\\n', so a `dataset: pilot` card saved with CRLF line endings or a
leading UTF-8 BOM (Windows authoring) parsed as having no frontmatter and slipped
past check_pilot_boundary — real customer data could be committed undetected.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import health_check  # noqa: E402


class FrontmatterEncodingTolerance(unittest.TestCase):
    def test_crlf_frontmatter_is_parsed(self) -> None:
        fm = health_check.frontmatter("---\r\ndataset: pilot\r\n---\r\nbody\r\n")
        self.assertEqual(fm.get("dataset"), "pilot", "a CRLF `dataset: pilot` card must not escape the check")

    def test_bom_frontmatter_is_parsed(self) -> None:
        fm = health_check.frontmatter("﻿---\ndataset: pilot\n---\nbody\n")
        self.assertEqual(fm.get("dataset"), "pilot", "a BOM-prefixed pilot card must not escape the check")

    def test_plain_lf_frontmatter_still_parses(self) -> None:
        # Regression: the common case keeps working.
        fm = health_check.frontmatter("---\ndataset: demo\n---\nbody\n")
        self.assertEqual(fm.get("dataset"), "demo")

    def test_non_frontmatter_still_returns_empty(self) -> None:
        self.assertEqual(health_check.frontmatter("# just a heading\n"), {})


if __name__ == "__main__":
    unittest.main()
