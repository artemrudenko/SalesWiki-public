"""Signed approvals: the worker and the live grant overlay must honor only
approvals produced by a holder of the approval key, so a forged `approved` line
appended to the proposal store neither writes a card nor unlocks a read. Legit
service-issued approvals still work end to end.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config, signing, worker  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.proposals import ProposalStore  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

COMPANY_ID = "demo-company-bluepeak-energy"


class SignedApprovals(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="signed-appr-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.audit = self.tmp / "audit.jsonl"
        self.proposals = self.tmp / "proposals.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(
            self.vault, self.audit, self.proposals, now=lambda: "2026-06-14T00:00:00Z"
        )

    def who(self, actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def deal_access(self, actor_id: str, company: str) -> str:
        return self.svc.deal_risk(self.who(actor_id), company)["access"]

    def _forge_approved(self, pid: str, **extra) -> None:
        """Append a forged approval with no valid signature (an attacker with only
        proposal-store write access, not the key)."""
        record = {"event": "approval_decision", "status": "approved",
                  "approver": "attacker", "approver_role": "admin",
                  "approved": "2026-06-14T00:00:00Z", "grant_expires": "2027-01-01T00:00:00Z"}
        record.update(extra)
        ProposalStore(self.proposals).append_status(pid, record)

    def test_forged_approval_is_not_applied_by_worker(self) -> None:
        pid = self.svc.flag_stale_or_wrong(self.who("demo-broad-viewer"), COMPANY_ID, "please check")
        self._forge_approved(pid)
        summary = worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "2026-06-14T01:00:00Z",
        )
        self.assertNotIn(pid, summary["applied"], "worker applied a forged approval")
        reasons = [f["reason"] for f in summary["failed"]]
        self.assertIn("unsigned-or-invalid-approval", reasons)

    def test_forged_grant_does_not_unlock_a_read(self) -> None:
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need it")
        self._forge_approved(pid, type="request_access")
        self.assertEqual(
            self.deal_access("demo-broad-viewer", "BluePeak Energy"),
            "blocked",
            "a forged approval must not unlock a restricted read",
        )

    def test_tampered_approver_role_is_rejected(self) -> None:
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need it")
        self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)  # legit, signed
        # Tamper: escalate approver_role to admin in the stored record.
        text = self.proposals.read_text(encoding="utf-8").replace(
            '"approver_role": "curator"', '"approver_role": "admin"'
        )
        self.proposals.write_text(text, encoding="utf-8")
        # The signature no longer matches, so the grant is dropped (fail closed).
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")

    def test_legit_signed_approval_still_works_end_to_end(self) -> None:
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need it")
        self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        summary = worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "2026-06-14T01:00:00Z",
        )
        self.assertIn(pid, summary["applied"])


class SigningUnit(unittest.TestCase):
    def test_sign_verify_roundtrip_and_tamper(self) -> None:
        key = b"0" * 32
        rec = {"proposal_id": "proposal-0001", "payload_hash": "sha256:x",
               "approver_role": "curator", "approved": "t", "grant_expires": "u"}
        rec["approval_sig"] = signing.sign(key, rec)
        self.assertTrue(signing.verify(key, rec))
        tampered = {**rec, "approver_role": "admin"}
        self.assertFalse(signing.verify(key, tampered))
        self.assertFalse(signing.verify(b"1" * 32, rec), "wrong key must not verify")


if __name__ == "__main__":
    unittest.main()
