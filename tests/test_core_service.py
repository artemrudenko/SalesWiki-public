"""Phase 3 tests: permissioned core service (identity, policy, retrieval, formatter, audit, proposals).

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


class IdentityResolution(unittest.TestCase):
    def test_fixture_user_maps_to_role(self) -> None:
        ethan = actor("demo-ethan-ae")
        self.assertEqual(ethan.role, "sales-owner")
        self.assertEqual(ethan.team, "sales-west")
        self.assertIn("demo-company-bluepeak-energy", ethan.owns)

    def test_role_resolved_from_env_not_client(self) -> None:
        env = {"SALESWIKI_DEMO_ACTOR": "demo-olivia-marketing"}
        resolved = FixtureIdentityProvider.from_env(config.identity_config(), env=env).resolve()
        self.assertEqual(resolved.role, "marketing")

    def test_unknown_actor_raises(self) -> None:
        with self.assertRaises(KeyError):
            FixtureIdentityProvider("nobody", config.identity_config()).resolve()


class CompanyBriefRoleContrast(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="core-"))
        self.svc = make_service(self.tmp)

    def test_sales_owner_sees_private_pricing(self) -> None:
        brief = self.svc.company_brief(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertTrue(any(s in brief["text"] for s in SALES_SECRETS), "owner must see sales-confidential detail")

    def test_marketing_blocked_from_named_deal(self) -> None:
        brief = self.svc.company_brief(actor("demo-olivia-marketing"), "BluePeak Energy")
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, brief["text"], f"secret {secret} leaked to marketing")
        self.assertEqual(brief["access"], "sanitized")

    def test_broad_viewer_sees_sanitized_summary(self) -> None:
        brief = self.svc.company_brief(actor("demo-broad-viewer"), "BluePeak Energy")
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, brief["text"])
        self.assertIn("BluePeak Energy", brief["text"])

    def test_no_salesconf_path_in_unauthorized_citations(self) -> None:
        brief = self.svc.company_brief(actor("demo-olivia-marketing"), "BluePeak Energy")
        joined = json.dumps(brief["citations"])
        self.assertNotIn("sales-confidential/wiki", joined, "restricted file path leaked in citations")

    def test_personal_data_shown_as_handle_for_non_admin(self) -> None:
        brief = self.svc.company_brief(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertIn("restricted://", brief["text"], "personal-data must appear as opaque handle, not raw body")

    def test_unknown_company_is_safe(self) -> None:
        brief = self.svc.company_brief(actor("demo-ethan-ae"), "Nonexistent Corp")
        self.assertEqual(brief["access"], "not-found")
        self.assertIn("missing", brief["text"].lower())

    def test_company_search_returns_only_discoverable_companies(self) -> None:
        owner = self.svc.company_search(actor("demo-ethan-ae"), "Blue")
        marketing = self.svc.company_search(actor("demo-olivia-marketing"), "Blue")
        self.assertEqual(owner["status"], "ok")
        self.assertEqual([item["label"] for item in owner["items"]], ["BluePeak Energy"])
        self.assertEqual([item["label"] for item in marketing["items"]], ["BluePeak Energy"])
        self.assertNotIn("Discount floor", json.dumps(marketing), "search must never expose card content")


class AuditAndProposals(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="core-"))
        self.svc = make_service(self.tmp)

    def test_audit_records_block_and_handle(self) -> None:
        self.svc.company_brief(actor("demo-olivia-marketing"), "BluePeak Energy")
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        decisions = {e["decision"] for e in events}
        self.assertIn("block", decisions)
        self.assertIn("handle", decisions)
        for e in events:
            self.assertEqual(e["actor"], "demo-olivia-marketing")
            self.assertEqual(e["role"], "marketing")

    def test_flag_is_append_only_proposal(self) -> None:
        before = sorted((self.tmp / "permissioned").rglob("*.md"))
        before_hashes = {p: p.read_bytes() for p in before}
        pid = self.svc.flag_stale_or_wrong(actor("demo-ethan-ae"), "demo-company-bluepeak-energy", "pricing looks stale")
        self.assertRegex(pid, r"^proposal-\d+$", "proposal id must follow the documented format")
        records = [json.loads(l) for l in (self.tmp / "proposals.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "draft")
        self.assertEqual(records[0]["target"], "demo-company-bluepeak-energy")
        # Production demo cards are untouched.
        for p, h in before_hashes.items():
            self.assertEqual(p.read_bytes(), h, f"{p} was mutated by a proposal")


if __name__ == "__main__":
    unittest.main()
