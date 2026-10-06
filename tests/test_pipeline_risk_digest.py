"""Slice 6 tests: role-aware pipeline_risk_digest.

pipeline_risk_digest aggregates the deals the actor may read (reusing deal_risk)
plus a count of pending proposals. HoS sees all deals, a sales owner only their
own, marketing only an aggregate with no named deal detail.
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


class PipelineRiskDigest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pipeline-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t")

    def test_hos_sees_all_deal_risk(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-claire-hos"))
        self.assertEqual(out["access"], "allowed")
        self.assertIn("title", out)
        self.assertIn("sections", out)
        self.assertIn("confidence", out)
        self.assertIn("freshness", out)
        for name in ("BluePeak Energy", "Northstar Robotics", "Atlas Foods"):
            self.assertIn(name, out["text"], f"HoS digest should include {name}")
        self.assertIn(RISK_HINT, out["text"])

    def test_owner_sees_only_own_deals(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-ethan-ae"))
        self.assertIn("BluePeak Energy", out["text"])
        self.assertNotIn("Northstar Robotics", out["text"], "owner must not see another team's named deal")

    def test_marketing_gets_aggregate_no_named_deals(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-olivia-marketing"))
        self.assertNotIn(RISK_HINT, out["text"])
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, out["text"])

    def test_digest_reports_pending_proposals(self) -> None:
        self.svc.flag_stale_or_wrong(actor("demo-ethan-ae"), "demo-company-bluepeak-energy", "stale pricing")
        out = self.svc.pipeline_risk_digest(actor("demo-claire-hos"))
        self.assertIn("ending proposal", out["text"], "digest should surface pending proposals")

    def test_audit_records_pipeline_digest(self) -> None:
        self.svc.pipeline_risk_digest(actor("demo-claire-hos"))
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "pipeline_risk_digest" for e in events))

    def test_hos_digest_has_quantified_rollup(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-claire-hos"))
        t = out["text"]
        self.assertIn("Open deals: 8", t)
        # Total pipeline = 240+310+180+420+360+220+340 = 2070k
        self.assertIn("$2,070k", t)
        # Weighted = 240*.55+310*.60+180*.35+420*.72+360*.48+220*.25+340*.65 = 1132.2k -> 1132k
        self.assertIn("Weighted pipeline", t)
        self.assertIn("$1,132k", t)
        # Stage breakdown present
        self.assertIn("Proposal 4", t)
        self.assertIn("Negotiation 2", t)

    def test_owner_rollup_scoped_to_visible_deals(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-ethan-ae"))
        t = out["text"]
        # Ethan sees five sales-west deals, including the dense graph fixture.
        # Its intentionally sparse commercial metadata must not inflate the
        # known-value rollup: 240+180+420+360 = 1200k.
        self.assertIn("Open deals: 5", t)
        self.assertIn("$1,200k", t)
        self.assertNotIn("$2,070k", t)

    def test_marketing_digest_has_no_rollup_numbers(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-olivia-marketing"))
        # No deal access -> no $ rollup may leak.
        self.assertNotIn("Total pipeline", out["text"])
        self.assertNotIn("Weighted pipeline", out["text"])
        self.assertNotIn("$", out["text"])

    def test_marketing_digest_is_explicitly_restricted_not_a_false_empty(self) -> None:
        # A role with no deal access must get an honest 'restricted/aggregated'
        # signal, not a generic 'review the deals' conclusion over an empty body.
        out = self.svc.pipeline_risk_digest(actor("demo-olivia-marketing"))
        self.assertEqual(out["access"], "aggregated")
        self.assertIn("restricted", out["conclusion"].lower())
        self.assertNotIn("Review the deals at risk", out["conclusion"])

    def test_hos_digest_access_stays_allowed(self) -> None:
        out = self.svc.pipeline_risk_digest(actor("demo-claire-hos"))
        self.assertEqual(out["access"], "allowed")
        self.assertIn("Review the deals at risk", out["conclusion"])

    def test_digest_renders_single_conclusion_and_footer(self) -> None:
        # The nested deal_risk answer's own conclusion/footer must not duplicate
        # the digest's, so the chat reader sees each once.
        t = self.svc.pipeline_risk_digest(actor("demo-claire-hos"))["text"]
        self.assertEqual(t.count("**Conclusion:**"), 1, "digest should show one Conclusion")
        self.assertEqual(t.count("**Access:**"), 1, "digest should show one Access footer")
        self.assertEqual(t.count("**Next action:**"), 1, "digest should show one Next action")

    def test_rollup_by_stage_in_pipeline_order(self) -> None:
        t = self.svc.pipeline_risk_digest(actor("demo-claire-hos"))["text"]
        self.assertIn("By stage: Qualification 1, Proposal 4, Negotiation 2, Unknown 1", t)


if __name__ == "__main__":
    unittest.main()
