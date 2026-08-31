"""Slice 10 unit tests for the Answer Contract envelope and renderer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp.answer import Answer, Citation, Section, Table, markdown_table, render  # noqa: E402


class Envelope(unittest.TestCase):
    def test_render_has_standard_footer_and_conclusion(self) -> None:
        ans = Answer(
            title="Deal Risk: BluePeak",
            access="allowed",
            conclusion="1 deal at risk.",
            sections=[Section("BluePeak", bullets=["Risk: economic buyer not engaged"])],
            citations=[Citation("sales-confidential", "deals/d.md")],
            next_action="confirm next step",
            as_of="2026-06-03",
        )
        text = render(ans)
        self.assertIn("# Deal Risk: BluePeak", text)
        self.assertIn("**Conclusion:** 1 deal at risk.", text)
        self.assertIn("**Access:** allowed", text)
        self.assertIn("**Sources:** sales-confidential: deals/d.md", text)
        self.assertIn("**As of:** 2026-06-03", text)

    def test_table_renders_as_markdown(self) -> None:
        rows = markdown_table(["Deal", "Risk"], [["BluePeak", "economic buyer"]])
        self.assertEqual(rows[0], "| Deal | Risk |")
        self.assertEqual(rows[1], "| --- | --- |")
        self.assertIn("| BluePeak | economic buyer |", rows[2])

    def test_table_cell_escapes_pipes_and_newlines(self) -> None:
        rows = markdown_table(["A"], [["x | y\nz"]])
        self.assertNotIn("\n", rows[2])
        self.assertIn("\\|", rows[2])

    def test_not_found_is_honest_with_missing_and_no_sections(self) -> None:
        ans = Answer.not_found("Deal Risk: Nobody", "no company card matched")
        self.assertEqual(ans.access, "not-found")
        self.assertEqual(ans.sections, [])
        text = render(ans)
        self.assertIn("## Missing", text)
        self.assertIn("no company card matched", text)

    def test_as_dict_exposes_structured_fields(self) -> None:
        ans = Answer(
            title="X", access="allowed", conclusion="c",
            sections=[Section("S", table=Table(["A"], [["1"]]))],
            citations=[Citation("broad", "c.md")],
        )
        d = ans.as_dict()
        self.assertEqual(d["access"], "allowed")
        self.assertEqual(d["sections"][0]["table"]["columns"], ["A"])
        self.assertEqual(d["citations"][0], {"boundary": "broad", "path": "c.md"})
        self.assertIn("text", d)


if __name__ == "__main__":
    unittest.main()
