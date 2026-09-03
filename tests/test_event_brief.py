"""Slice 3 tests: role-aware event_brief over the permissioned core.

event_brief lists an event's target accounts (broad, every role sees them) and
adds private deal context per account only for roles that may read that deal.
Marketing gets the brief without restricted deal details.
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
EVENT = "Sales Tech Summit 2026"
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


class EventBrief(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="event-brief-"))
        self.svc = make_service(self.tmp)

    def test_all_roles_see_target_accounts(self) -> None:
        for who in ("demo-ethan-ae", "demo-olivia-marketing", "demo-broad-viewer"):
            out = self.svc.event_brief(actor(who), EVENT)
            self.assertEqual(out["access"], "allowed", who)
            for name in COMPANY_NAMES:
                self.assertIn(name, out["text"], f"{who} should see target account {name}")

    def test_sales_sees_deal_detail_marketing_does_not(self) -> None:
        owner = self.svc.event_brief(actor("demo-ethan-ae"), EVENT)
        mkt = self.svc.event_brief(actor("demo-olivia-marketing"), EVENT)
        self.assertIn(RISK_HINT, owner["text"], "owner must see deal context for their accounts")
        self.assertNotIn(RISK_HINT, mkt["text"], "marketing must get no restricted deal detail")

    def test_no_sales_secret_leaks_to_marketing(self) -> None:
        out = self.svc.event_brief(actor("demo-olivia-marketing"), EVENT)
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, out["text"])

    def test_deal_context_reads_cleanly(self) -> None:
        owner = self.svc.event_brief(actor("demo-ethan-ae"), EVENT)["text"]
        self.assertNotIn(".;", owner, "risk period should not collide with the guidance separator")
        self.assertIn("tie the message to it", owner)

    def test_no_salesconf_path_in_marketing_citations(self) -> None:
        out = self.svc.event_brief(actor("demo-olivia-marketing"), EVENT)
        self.assertNotIn("sales-confidential/wiki", json.dumps(out["citations"]))

    def test_unknown_event_is_safe(self) -> None:
        out = self.svc.event_brief(actor("demo-ethan-ae"), "Nonexistent Expo")
        self.assertEqual(out["access"], "not-found")

    def test_audit_records_event_brief(self) -> None:
        self.svc.event_brief(actor("demo-ethan-ae"), EVENT)
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "event_brief" for e in events))

    def test_does_not_mutate_production(self) -> None:
        before = {p: p.read_bytes() for p in (self.tmp / "permissioned").rglob("*.md")}
        self.svc.event_brief(actor("demo-ethan-ae"), EVENT)
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by a read")


if __name__ == "__main__":
    unittest.main()
