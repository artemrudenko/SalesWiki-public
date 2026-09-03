"""Arch #3/#4 tests: strict entity resolution + data-derived freshness.

#3 - find() must never silently return the wrong entity: exact id/display wins,
a substring is accepted only when unique, ambiguous resolves to None and the tool
surfaces candidates honestly. #4 - answers report freshness/as_of derived from the
card, not a hardcoded constant.
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
from saleswiki_mcp.retrieval import Retriever  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class StrictResolver(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="resolve-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        # Two companies sharing a token, to force ambiguity.
        comp = self.vault / "broad" / "wiki" / "entities" / "companies"
        for name, slug in [("Acme Foods", "acme-foods"), ("Acme Robotics", "acme-robotics")]:
            (comp / f"Company - {name}.md").write_text(
                f"---\ntype: company\nentity_id: demo-company-{slug}\ndataset: demo\nsynthetic: true\n"
                f"boundary: broad\nfreshness: stale\nupdated: 2026-01-01\n---\n# Company: {name}\n",
                encoding="utf-8",
            )
        self.retriever = Retriever(self.vault, config.boundary_registry())

    def test_exact_display_wins(self) -> None:
        self.assertEqual(self.retriever.find("Acme Foods", "company").entity_id, "demo-company-acme-foods")

    def test_ambiguous_substring_returns_none(self) -> None:
        self.assertIsNone(self.retriever.find("Acme", "company"), "ambiguous query must not resolve to one card")

    def test_candidates_lists_all_matches(self) -> None:
        names = sorted(c.display for c in self.retriever.candidates("Acme", "company"))
        self.assertEqual(names, ["Acme Foods", "Acme Robotics"])

    def test_unique_substring_still_resolves(self) -> None:
        self.assertEqual(self.retriever.find("BluePeak", "company").entity_id, "demo-company-bluepeak-energy")

    def test_company_brief_is_ambiguous_not_wrong(self) -> None:
        svc = build_default_service(self.vault, self.tmp / "a.jsonl", self.tmp / "p.jsonl", now=lambda: "t")
        out = svc.company_brief(actor("demo-ethan-ae"), "Acme")
        self.assertEqual(out["access"], "ambiguous")
        self.assertIn("Acme Foods", out["text"])
        self.assertIn("Acme Robotics", out["text"])


class DataDerivedFreshness(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fresh-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(self.vault, self.tmp / "a.jsonl", self.tmp / "p.jsonl", now=lambda: "t")

    def test_freshness_reflects_card_not_constant(self) -> None:
        out = self.svc.company_brief(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertEqual(out["freshness"], "fresh", "demo cards are fresh; value must come from data")
        self.assertTrue(out["as_of"], "as_of should be the card's updated date")
        self.assertNotIn("fresh (synthetic demo)", out["text"], "no hardcoded freshness constant")

    def test_stale_card_reports_stale(self) -> None:
        card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"
        card.write_text(card.read_text(encoding="utf-8").replace("freshness: fresh", "freshness: stale"), encoding="utf-8")
        out = self.svc.company_brief(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertEqual(out["freshness"], "stale", "a stale card must not be reported as fresh")


if __name__ == "__main__":
    unittest.main()
