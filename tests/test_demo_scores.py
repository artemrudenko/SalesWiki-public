"""Tests: the permissioned demo cards carry numeric scores/metrics, not just bands.

The bridge serves the permissioned demo vault, so demo quality depends on real
numbers (lead score, deal score, win probability, deal value, days-in-stage)
being present and extractable via the field-extraction profile.
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


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class DemoCardNumbers(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="demo-scores-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(
            self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t"
        )
        self.retriever = self.svc._retriever

    def _deal(self, company_slug: str):
        return self.retriever.related_by_type(f"demo-company-{company_slug}", "deal")[0]

    def _lead(self, company_slug: str):
        return self.retriever.related_by_type(f"demo-company-{company_slug}", "lead")[0]

    def test_deal_card_has_numeric_score(self) -> None:
        deal = self._deal("bluepeak-energy")
        score = self.svc._field(deal, "score")
        self.assertTrue(score.isdigit(), f"deal score should be numeric, got {score!r}")

    def test_deal_card_has_win_probability_and_value(self) -> None:
        deal = self._deal("bluepeak-energy")
        self.assertIn("%", self.svc._field(deal, "win_probability"))
        self.assertTrue(self.svc._field(deal, "acv").startswith("$"))

    def test_deal_card_has_days_in_stage(self) -> None:
        deal = self._deal("bluepeak-energy")
        self.assertTrue(self.svc._field(deal, "days_in_stage").isdigit())

    def test_deal_scores_vary_across_companies(self) -> None:
        scores = {
            slug: self.svc._field(self._deal(slug), "score")
            for slug in ("bluepeak-energy", "meridian-payments", "atlas-foods")
        }
        self.assertEqual(len(set(scores.values())), 3, f"scores should vary, got {scores}")

    def test_lead_card_has_numeric_score_and_band(self) -> None:
        lead = self._lead("bluepeak-energy")
        self.assertTrue(self.svc._field(lead, "score").isdigit())
        self.assertEqual(self.svc._field(lead, "score_band"), "hot")


if __name__ == "__main__":
    unittest.main()
