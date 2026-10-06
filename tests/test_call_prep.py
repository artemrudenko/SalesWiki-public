"""Slice 2 tests: role-aware call_prep over the permissioned core.

call_prep gives authorized sales a sanitized pre-call summary plus an opaque
handle to the raw transcript (never the raw body), and gives marketing only a
sanitized "sales feedback only" note with no named deal detail. Sensitive call
content must never appear in the prep output for any role.
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
CALL_SECRETS = ("internal budget", "RivalCorp")


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


class CallPrep(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="call-prep-"))
        self.svc = make_service(self.tmp)

    def test_owner_gets_sanitized_prep_and_raw_handle(self) -> None:
        out = self.svc.call_prep(actor("demo-ethan-ae"), "BluePeak Energy")
        self.assertEqual(out["access"], "allowed")
        self.assertIn("Sanitized takeaway", out["text"])
        self.assertTrue(out["restricted"], "raw transcript must be surfaced as a restricted handle")
        self.assertIn("restricted://", json.dumps(out))

    def test_hos_also_allowed(self) -> None:
        out = self.svc.call_prep(actor("demo-claire-hos"), "BluePeak Energy")
        self.assertEqual(out["access"], "allowed")
        self.assertIn("Sanitized takeaway", out["text"])

    def test_call_secrets_never_in_prep_for_any_role(self) -> None:
        for who in ("demo-ethan-ae", "demo-claire-hos", "demo-olivia-marketing"):
            out = self.svc.call_prep(actor(who), "BluePeak Energy")
            for secret in CALL_SECRETS:
                self.assertNotIn(secret, out["text"], f"{secret} leaked to {who}")

    def test_marketing_gets_sanitized_note_no_deal_detail(self) -> None:
        out = self.svc.call_prep(actor("demo-olivia-marketing"), "BluePeak Energy")
        self.assertEqual(out["access"], "sanitized")
        self.assertNotIn("Sanitized takeaway", out["text"], "marketing must not get the call conclusion body")
        self.assertNotIn("restricted://", json.dumps(out), "marketing must not get the raw transcript handle")
        for secret in SALES_SECRETS + CALL_SECRETS:
            self.assertNotIn(secret, out["text"])

    def test_no_salesconf_path_in_marketing_citations(self) -> None:
        out = self.svc.call_prep(actor("demo-olivia-marketing"), "BluePeak Energy")
        self.assertNotIn("sales-confidential/wiki", json.dumps(out["citations"]))

    def test_unknown_company_is_safe(self) -> None:
        out = self.svc.call_prep(actor("demo-ethan-ae"), "Nonexistent Corp")
        self.assertEqual(out["access"], "not-found")

    def test_audit_records_call_prep(self) -> None:
        self.svc.call_prep(actor("demo-ethan-ae"), "BluePeak Energy")
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "call_prep" for e in events))

    def test_does_not_mutate_production(self) -> None:
        before = {p: p.read_bytes() for p in (self.tmp / "permissioned").rglob("*.md")}
        self.svc.call_prep(actor("demo-ethan-ae"), "BluePeak Energy")
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by a read")


if __name__ == "__main__":
    unittest.main()
