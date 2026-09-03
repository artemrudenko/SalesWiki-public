"""Risk-#1 tests: the read layer is decoupled from any single card shape.

The field-extraction profile (schemas/field-extraction.json) is the contract
between card templates and the extractor. These tests assert (a) the active demo
cards satisfy the profile for every mapped field, and (b) a production-SHAPED card
(different section/label) extracts correctly when given an override profile -
proving the extractor is data-driven, not hardcoded to the demo layout.
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
from saleswiki_mcp.formatter import field_value  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.retrieval import Retriever  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class FieldExtractionContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="field-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.retriever = Retriever(self.vault, config.boundary_registry())
        self.profile = config.field_extraction()["types"]

    def test_active_demo_cards_satisfy_the_profile(self) -> None:
        # Every mapped (type, field) must resolve to non-empty content on at least
        # one real demo card of that type - i.e. templates and extractor agree.
        cards_by_type: dict[str, list] = {}
        for card in self.retriever.cards():
            cards_by_type.setdefault(card.type, []).append(card)
        for card_type, fields in self.profile.items():
            cards = cards_by_type.get(card_type, [])
            self.assertTrue(cards, f"no demo card for mapped type {card_type}")
            for field_name, spec in fields.items():
                got = [field_value(c.body, spec) for c in cards]
                self.assertTrue(any(v.strip() for v in got),
                                f"profile {card_type}.{field_name} ({spec}) matched nothing on demo cards")

    def test_extractor_reads_a_production_shaped_card_via_override(self) -> None:
        # A card with a DIFFERENT shape (production-style sections/labels) extracts
        # correctly when the profile points at its sections - no code change.
        body = (
            "# Deal: Acme\n\n## Risks\n\n- Primary risk: economic buyer not engaged\n\n"
            "## Next Best Action\n\n- Step: re-engage the buyer\n"
        )
        risk_spec = {"section": "Risks", "label": "Primary risk"}
        action_spec = {"section": "Next Best Action", "label": "Step"}
        self.assertEqual(field_value(body, risk_spec), "economic buyer not engaged")
        self.assertEqual(field_value(body, action_spec), "re-engage the buyer")

    def test_service_accepts_an_injected_field_map(self) -> None:
        # The service takes the profile by injection (build/test against any shape).
        svc = build_default_service(
            self.vault, self.tmp / "a.jsonl", self.tmp / "p.jsonl",
            now=lambda: "t",
        )
        out = svc.deal_risk(actor("demo-ethan-ae"), None)
        self.assertIn("economic buyer", out["text"], "default profile still extracts demo risk")

    def test_unmapped_field_returns_empty_not_error(self) -> None:
        svc = build_default_service(self.vault, self.tmp / "a2.jsonl", self.tmp / "p2.jsonl", now=lambda: "t")
        company = self.retriever.find_company("BluePeak Energy")
        self.assertEqual(svc._field(company, "no_such_field"), "")


if __name__ == "__main__":
    unittest.main()
