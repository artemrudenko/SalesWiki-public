"""Slice 10 invariant tests: every read tool obeys the Answer Contract.

Enforces the accuracy guarantees uniformly: the structured envelope is present,
every non-missing answer carries a citation (provenance), an absent target yields
an honest not-found with a Missing note and no fabricated sections, and record
lists render a Markdown table.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

ENVELOPE_KEYS = {"title", "access", "conclusion", "sections", "citations", "restricted",
                 "confidence", "freshness", "next_action", "missing", "text"}
ACCESS_VALUES = {"allowed", "sanitized", "aggregated", "blocked", "not-found", "ambiguous"}


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class AnswerContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="contract-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t")
        self.a = actor("demo-ivan-ae")
        self.answers = [
            self.svc.company_brief(self.a, "BluePeak Energy"),
            self.svc.deal_risk(self.a, None),
            self.svc.call_prep(self.a, "BluePeak Energy"),
            self.svc.lead_priority(self.a, None),
            self.svc.event_brief(self.a, "Sales Tech Summit 2026"),
            self.svc.my_day(self.a),
            self.svc.pipeline_risk_digest(self.a),
            self.svc.campaign_brief(self.a, "Q3 ROI Push"),
            self.svc.content_opportunities(self.a),
        ]

    def test_every_answer_has_the_envelope(self) -> None:
        for ans in self.answers:
            self.assertTrue(ENVELOPE_KEYS.issubset(ans.keys()), f"missing keys: {ENVELOPE_KEYS - ans.keys()}")
            self.assertIn(ans["access"], ACCESS_VALUES)

    def test_non_missing_answers_carry_provenance(self) -> None:
        for ans in self.answers:
            if ans["access"] in ("allowed", "sanitized"):
                self.assertTrue(ans["citations"], f"{ans['title']} emitted content without a citation")

    def test_record_list_tools_render_a_table(self) -> None:
        for out in (self.svc.deal_risk(self.a, None), self.svc.lead_priority(self.a, None), self.svc.content_opportunities(self.a)):
            self.assertIn("| --- |", out["text"], f"{out['title']} should render a Markdown table")
            self.assertTrue(any(s.get("table") for s in out["sections"]))

    def test_absent_target_is_honest_not_found(self) -> None:
        for out in (
            self.svc.company_brief(self.a, "No Such Co"),
            self.svc.deal_risk(self.a, "No Such Co"),
            self.svc.campaign_brief(self.a, "No Such Campaign"),
        ):
            self.assertEqual(out["access"], "not-found")
            self.assertTrue(out["missing"], "not-found must state what is missing")
            self.assertEqual(out["sections"], [], "not-found must not fabricate sections")
            self.assertIn("missing", out["text"].lower())

    def test_footer_carries_confidence_and_access(self) -> None:
        for ans in self.answers:
            self.assertIn("**Confidence:**", ans["text"])
            self.assertIn(f"**Access:** {ans['access']}", ans["text"])


if __name__ == "__main__":
    unittest.main()
