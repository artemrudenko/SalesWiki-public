"""Slice 6 tests: role-aware my_day digest.

my_day composes the actor's lead_priority and deal_risk into one "what to do
today" answer. Because it reuses the access-filtered read products, no-leak is
inherited: a sales owner sees their at-risk deals, marketing sees the broad lead
list but no deal detail, and no sales-confidential secret reaches an unauthorized
role.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import json
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

SALES_SECRETS = ("Discount floor", "Pricing:", "ACV")
RISK_HINT = "economic buyer"


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class MyDay(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="my-day-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t")

    def test_owner_sees_leads_and_deal_risk(self) -> None:
        out = self.svc.my_day(actor("demo-ethan-ae"))
        self.assertEqual(out["access"], "allowed")
        self.assertIn("title", out)
        self.assertIn("sections", out)
        self.assertIn("confidence", out)
        self.assertIn("freshness", out)
        self.assertIn("BluePeak Energy", out["text"])
        self.assertIn(RISK_HINT, out["text"], "owner should see at-risk deals in their day")

    def test_marketing_sees_leads_but_no_deal_detail(self) -> None:
        out = self.svc.my_day(actor("demo-olivia-marketing"))
        self.assertIn("BluePeak Energy", out["text"], "marketing still gets the broad lead list")
        self.assertNotIn(RISK_HINT, out["text"], "marketing gets no deal detail")
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, out["text"])

    def test_audit_records_my_day(self) -> None:
        self.svc.my_day(actor("demo-ethan-ae"))
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "my_day" for e in events))

    def test_does_not_mutate_production(self) -> None:
        before = {p: p.read_bytes() for p in self.vault.rglob("*.md")}
        self.svc.my_day(actor("demo-ethan-ae"))
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by a read")


if __name__ == "__main__":
    unittest.main()
