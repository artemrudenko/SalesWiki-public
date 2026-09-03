"""Slice 8 tests: Marketing Workbench - campaign_brief + content_opportunities.

content_opportunities is a broad marketing product (pain points + content angle)
every role can see. campaign_brief lists public target accounts for all roles and
adds per-account deal context only for roles that may read the deal; marketing
gets the brief without restricted deal detail.
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
CAMPAIGN = "Q3 ROI Push"
COMPANY_NAMES = ("BluePeak Energy", "Northstar Robotics", "Atlas Foods")


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class MarketingWorkbench(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mktg-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t")

    # -- content_opportunities --------------------------------------------
    def test_content_opportunities_visible_to_all_roles(self) -> None:
        for who in ("demo-olivia-marketing", "demo-broad-viewer", "demo-ethan-ae"):
            out = self.svc.content_opportunities(actor(who))
            self.assertEqual(out["access"], "allowed", who)
            self.assertIn("Content angle", out["text"])
            self.assertIn("Energy cost volatility", out["text"])

    def test_content_opportunities_has_no_sales_secret(self) -> None:
        out = self.svc.content_opportunities(actor("demo-olivia-marketing"))
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, out["text"])

    # -- campaign_brief ----------------------------------------------------
    def test_campaign_brief_lists_target_accounts_for_all(self) -> None:
        for who in ("demo-olivia-marketing", "demo-ethan-ae"):
            out = self.svc.campaign_brief(actor(who), CAMPAIGN)
            self.assertEqual(out["access"], "allowed", who)
            for name in COMPANY_NAMES:
                self.assertIn(name, out["text"], f"{who} should see {name}")

    def test_campaign_brief_sales_sees_deal_marketing_does_not(self) -> None:
        owner = self.svc.campaign_brief(actor("demo-ethan-ae"), CAMPAIGN)
        mkt = self.svc.campaign_brief(actor("demo-olivia-marketing"), CAMPAIGN)
        self.assertIn(RISK_HINT, owner["text"], "sales owner sees deal context for owned accounts")
        self.assertNotIn(RISK_HINT, mkt["text"], "marketing gets no restricted deal detail")
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, mkt["text"])
        self.assertNotIn("sales-confidential/wiki", json.dumps(mkt["citations"]))

    def test_campaign_brief_public_angle_cites_its_source_card(self) -> None:
        # The "public angle" text is extracted verbatim from a Source card; that
        # card must be cited, not silently attributed to the campaign card (the
        # only card cited before this fix). Mandatory-provenance / extract-with-
        # citation contract.
        mkt = self.svc.campaign_brief(actor("demo-olivia-marketing"), CAMPAIGN)
        self.assertIn("public angle", mkt["text"], "precondition: marketing sees a public-angle row")
        self.assertIn(
            "Source -", json.dumps(mkt["citations"]),
            "the market-signal source card must be cited, not attributed to the campaign card",
        )

    def test_unknown_campaign_is_safe(self) -> None:
        out = self.svc.campaign_brief(actor("demo-ethan-ae"), "No Such Campaign")
        self.assertEqual(out["access"], "not-found")

    def test_audit_records_marketing_tools(self) -> None:
        self.svc.content_opportunities(actor("demo-olivia-marketing"))
        self.svc.campaign_brief(actor("demo-olivia-marketing"), CAMPAIGN)
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        tools = {e["tool"] for e in events}
        self.assertIn("content_opportunities", tools)
        self.assertIn("campaign_brief", tools)

    def test_does_not_mutate_production(self) -> None:
        before = {p: p.read_bytes() for p in self.vault.rglob("*.md")}
        self.svc.content_opportunities(actor("demo-olivia-marketing"))
        self.svc.campaign_brief(actor("demo-ethan-ae"), CAMPAIGN)
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by a read")


if __name__ == "__main__":
    unittest.main()
