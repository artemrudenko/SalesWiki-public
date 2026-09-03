"""Slice 2 tests: role-aware deal_risk over the permissioned core.

deal_risk answers "which deals are at risk and what to do next" while honoring
the same RBAC+ABAC boundaries as company_brief: a sales owner sees only their
own/team deals, HoS sees all, and marketing gets an aggregated count with no
named deal detail and no sales-confidential leakage.
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
COMPANY_NAMES = ("BluePeak Energy", "Northstar Robotics", "Atlas Foods")


def make_service(tmp: Path):
    vault = tmp / "permissioned"
    gdv.generate_permissioned_demo(vault)
    return build_default_service(
        vault_root=vault,
        audit_path=tmp / "audit.jsonl",
        proposal_path=tmp / "proposals.jsonl",
        now=lambda: "2026-06-03T00:00:00Z",
    )


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class DealRisk(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="deal-risk-"))
        self.svc = make_service(self.tmp)

    def test_owner_sees_own_deal_risk_by_company(self) -> None:
        out = self.svc.deal_risk(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertEqual(out["access"], "allowed")
        self.assertIn("economic buyer", out["text"].lower())
        self.assertIn("BluePeak Energy", out["text"])

    def test_owner_all_accessible_lists_only_owned_or_team(self) -> None:
        out = self.svc.deal_risk(actor("demo-ethan-ae"), None)
        self.assertEqual(out["access"], "allowed")
        self.assertIn("BluePeak Energy", out["text"])
        self.assertIn("Atlas Foods", out["text"])
        self.assertNotIn("Northstar Robotics", out["text"], "Ethan must not see the sales-east deal")

    def test_hos_sees_all_deals(self) -> None:
        out = self.svc.deal_risk(actor("demo-claire-hos"), None)
        self.assertEqual(out["access"], "allowed")
        for name in COMPANY_NAMES:
            self.assertIn(name, out["text"], f"HoS must see {name}")

    def test_marketing_gets_aggregated_count_without_names(self) -> None:
        out = self.svc.deal_risk(actor("demo-olivia-marketing"), None)
        self.assertEqual(out["access"], "aggregated")
        for name in COMPANY_NAMES:
            self.assertNotIn(name, out["text"], "aggregated view must not name deals")
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, out["text"])

    def test_marketing_blocked_for_named_company(self) -> None:
        out = self.svc.deal_risk(actor("demo-olivia-marketing"), "BluePeak Energy")
        self.assertEqual(out["access"], "blocked")
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, out["text"])

    def test_no_salesconf_path_in_marketing_citations(self) -> None:
        out = self.svc.deal_risk(actor("demo-olivia-marketing"), None)
        self.assertNotIn("sales-confidential/wiki", json.dumps(out["citations"]))

    def test_unknown_company_is_safe(self) -> None:
        out = self.svc.deal_risk(actor("demo-ethan-ae"), "Nonexistent Corp")
        self.assertEqual(out["access"], "not-found")

    def test_audit_records_deal_risk(self) -> None:
        self.svc.deal_risk(actor("demo-ethan-ae"), None)
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "deal_risk" for e in events))

    def test_does_not_mutate_production(self) -> None:
        before = {p: p.read_bytes() for p in (self.tmp / "permissioned").rglob("*.md")}
        self.svc.deal_risk(actor("demo-claire-hos"), None)
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by a read")


if __name__ == "__main__":
    unittest.main()
