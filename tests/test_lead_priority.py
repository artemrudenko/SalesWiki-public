"""Slice 3 tests: role-aware lead_priority over the permissioned core.

lead_priority ranks broad MQL leads that every role may see (band + why-now +
next action), keeps the contact as an opaque handle, and enriches the result
with the linked deal's risk only for roles that may read that deal. Sales-secret
content never leaks; marketing gets no linked-deal detail.
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


class LeadPriority(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lead-prio-"))
        self.svc = make_service(self.tmp)

    def test_all_roles_get_the_ranked_list(self) -> None:
        for who in ("demo-ethan-ae", "demo-olivia-marketing", "demo-broad-viewer"):
            out = self.svc.lead_priority(actor(who), None)
            self.assertEqual(out["access"], "allowed", who)
            for name in COMPANY_NAMES:
                self.assertIn(name, out["text"], f"{who} should see {name}")

    def test_funnel_spans_mql_sql_and_nurture(self) -> None:
        out = self.svc.lead_priority(actor("demo-olivia-marketing"), None)
        text = out["text"]
        for stage in ("SQL", "MQL", "nurture"):
            self.assertIn(stage, text, f"funnel should surface {stage}")
        self.assertIn("Vertex Logistics", text)
        self.assertIn("Orchard Bank", text)

    def test_mql_prospect_has_no_linked_deal(self) -> None:
        out = self.svc.lead_priority(actor("demo-claire-hos"), "Vertex Logistics")
        self.assertIn("no linked deal", out["text"])

    def test_hot_lead_ranked_before_warm(self) -> None:
        out = self.svc.lead_priority(actor("demo-olivia-marketing"), None)
        text = out["text"]
        self.assertLess(text.index("BluePeak Energy"), text.index("Northstar Robotics"), "hot lead must rank first")

    def test_contact_is_opaque_handle_for_non_admin(self) -> None:
        out = self.svc.lead_priority(actor("demo-ethan-ae"), None)
        self.assertIn("restricted://", json.dumps(out))

    def test_sales_sees_linked_deal_risk_marketing_does_not(self) -> None:
        owner = self.svc.lead_priority(actor("demo-ethan-ae"), None)
        mkt = self.svc.lead_priority(actor("demo-olivia-marketing"), None)
        self.assertIn(RISK_HINT, owner["text"], "owner must see linked deal risk for their accounts")
        self.assertNotIn(RISK_HINT, mkt["text"], "marketing must not see linked deal risk")

    def test_owner_only_enriches_own_accounts(self) -> None:
        out = self.svc.lead_priority(actor("demo-ethan-ae"), None)
        # Ethan owns BluePeak + Atlas (sales-west) but not Northstar (sales-east):
        # the Northstar lead is still listed, but without linked-deal enrichment.
        self.assertIn("Northstar Robotics", out["text"])

    def test_no_sales_secret_leaks_for_any_role(self) -> None:
        for who in ("demo-ethan-ae", "demo-olivia-marketing", "demo-broad-viewer"):
            out = self.svc.lead_priority(actor(who), None)
            for secret in SALES_SECRETS:
                self.assertNotIn(secret, out["text"], f"{secret} leaked to {who}")

    def test_company_arg_filters_to_one_lead(self) -> None:
        out = self.svc.lead_priority(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertIn("BluePeak Energy", out["text"])
        self.assertNotIn("Atlas Foods", out["text"])

    def test_unknown_company_is_safe(self) -> None:
        out = self.svc.lead_priority(actor("demo-ethan-ae"), "Nonexistent Corp")
        self.assertEqual(out["access"], "not-found")

    def test_audit_records_lead_priority(self) -> None:
        self.svc.lead_priority(actor("demo-ethan-ae"), None)
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "lead_priority" for e in events))

    def test_does_not_mutate_production(self) -> None:
        before = {p: p.read_bytes() for p in (self.tmp / "permissioned").rglob("*.md")}
        self.svc.lead_priority(actor("demo-ethan-ae"), None)
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by a read")


if __name__ == "__main__":
    unittest.main()
