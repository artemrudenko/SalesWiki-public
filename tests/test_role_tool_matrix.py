"""Slice 7 tests: full role x tool access matrix + correct 'assigned' ABAC.

Exercises every fixture role against every read tool to prove the access model
holds across the whole org, not just the four roles used elsewhere. Also pins
the SDR 'assigned' constraint as strictly narrower than a sales owner's
'owned_or_team' (an unassigned SDR sees no deal it does not own).
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
from saleswiki_mcp.policy import PolicyEvaluator, Resource  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

SALES_SECRETS = ("Discount floor", "Pricing:", "ACV")
RISK_HINT = "economic buyer"

# Roles that must never see sales-confidential secrets in any read tool.
NO_SECRET_ROLES = ["demo-broad-viewer", "demo-sam-sdr", "demo-nina-marketing", "demo-lena-legal"]
# Roles that should see deal risk in deal_risk(None).
RISK_PRESENT = ["demo-ivan-ae", "demo-elena-hos", "demo-raj-revops", "demo-marina-curator", "demo-ada-admin"]
RISK_ABSENT = ["demo-broad-viewer", "demo-sam-sdr", "demo-nina-marketing", "demo-lena-legal"]


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class RoleToolMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="matrix-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t")
        self.read_calls = [
            lambda a: self.svc.company_brief(a, "BluePeak Energy"),
            lambda a: self.svc.deal_risk(a, None),
            lambda a: self.svc.call_prep(a, "BluePeak Energy"),
            lambda a: self.svc.lead_priority(a, None),
            lambda a: self.svc.event_brief(a, "Sales Tech Summit 2026"),
            lambda a: self.svc.my_day(a),
            lambda a: self.svc.pipeline_risk_digest(a),
            lambda a: self.svc.entity_graph(a, "BluePeak Energy"),
        ]

    def test_all_fixture_roles_resolve(self) -> None:
        known_roles = {r["id"] for r in config.access_policy()["roles"]}
        for aid in NO_SECRET_ROLES + RISK_PRESENT:
            self.assertIn(actor(aid).role, known_roles,
                          f"{aid} must resolve to a role defined in the access policy")

    def test_every_tool_answers_safely_for_every_role(self) -> None:
        for aid in set(NO_SECRET_ROLES + RISK_PRESENT):
            for call in self.read_calls:
                out = call(actor(aid))
                self.assertIn("access", out, f"{aid} tool returned no access field")
                self.assertIn("text", out)

    def test_no_secret_roles_never_see_sales_secrets(self) -> None:
        for aid in NO_SECRET_ROLES:
            for call in self.read_calls:
                text = call(actor(aid))["text"]
                for secret in SALES_SECRETS:
                    self.assertNotIn(secret, text, f"{secret} leaked to {aid}")

    def test_graph_structured_payload_never_leaks_to_restricted_roles(self) -> None:
        for aid in NO_SECRET_ROLES:
            payload = json.dumps(self.svc.entity_graph(actor(aid), "BluePeak Energy"))
            for secret in (*SALES_SECRETS, "RivalCorp", "economic buyer"):
                self.assertNotIn(secret, payload, f"{secret} leaked in graph payload to {aid}")

    def test_deal_risk_visibility_matches_role(self) -> None:
        for aid in RISK_PRESENT:
            self.assertIn(RISK_HINT, self.svc.deal_risk(actor(aid), None)["text"], f"{aid} should see deal risk")
        for aid in RISK_ABSENT:
            self.assertNotIn(RISK_HINT, self.svc.deal_risk(actor(aid), None)["text"], f"{aid} must not see deal risk")

    def test_sdr_assigned_is_narrower_than_owner_team(self) -> None:
        # A deal owned by Ivan on team sales-west: the AE (owned_or_team) sees it,
        # but an unassigned SDR on the same team (assigned) does not.
        policy = PolicyEvaluator(config.access_policy())
        deal = Resource(entity_id="demo-deal-bluepeak-energy-pilot", boundary="sales-confidential",
                        owner="demo-ivan-ae", team="sales-west", company="demo-company-bluepeak-energy")
        self.assertEqual(policy.can_read(actor("demo-ivan-ae"), deal).effect, "allow")
        self.assertEqual(policy.can_read(actor("demo-sam-sdr"), deal).effect, "block",
                         "an unassigned SDR must not see a team-mate's deal")

    def test_admin_reads_personal_data_others_get_handle(self) -> None:
        policy = PolicyEvaluator(config.access_policy())
        pd = Resource(entity_id="x", boundary="personal-data")
        self.assertEqual(policy.can_read(actor("demo-ada-admin"), pd).effect, "allow")
        self.assertEqual(policy.can_read(actor("demo-nina-marketing"), pd).effect, "handle")

    def test_legal_reviewer_blocked_from_sales_confidential(self) -> None:
        policy = PolicyEvaluator(config.access_policy())
        deal = Resource(entity_id="d", boundary="sales-confidential", owner="x", team="y", company="z")
        self.assertEqual(policy.can_read(actor("demo-lena-legal"), deal).effect, "block")


if __name__ == "__main__":
    unittest.main()
