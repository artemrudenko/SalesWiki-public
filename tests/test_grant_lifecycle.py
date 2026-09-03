"""Grant lifecycle: revoke, time-boxed expiry, and the admin-only personal-data
scope. Builds on test_grant_access (approve = scoped sales-confidential grant).
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
from saleswiki_mcp import config, worker  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.proposals import ProposalStore  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

COMPANY_ID = "demo-company-bluepeak-energy"


class GrantLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="grant-life-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.clock = {"t": "2026-06-14T00:00:00Z"}
        self.svc = build_default_service(
            self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl",
            now=lambda: self.clock["t"],
        )

    def who(self, actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def deal_access(self, actor_id: str, company: str) -> str:
        return self.svc.deal_risk(self.who(actor_id), company)["access"]

    def brief_access(self, actor_id: str) -> str:
        return self.svc.company_brief(self.who(actor_id), "BluePeak Energy")["access"]

    def _granted_pid(self, approver: str = "demo-sophie-curator", ttl_days: int = 30) -> str:
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need it")
        self.svc.approve_proposal(self.who(approver), pid, ttl_days=ttl_days)
        return pid

    def test_revoke_drops_the_grant(self) -> None:
        pid = self._granted_pid()
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        out = self.svc.revoke_proposal(self.who("demo-sophie-curator"), pid, "no longer needed")
        self.assertEqual(out["status"], "revoked")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")

    def test_non_approver_cannot_revoke(self) -> None:
        pid = self._granted_pid()
        out = self.svc.revoke_proposal(self.who("demo-sam-sdr"), pid, "trying")
        self.assertEqual(out["status"], "blocked")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")

    def test_grant_expires(self) -> None:
        self._granted_pid(ttl_days=1)  # expires 2026-06-15
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        self.clock["t"] = "2026-06-16T00:00:00Z"  # past expiry
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")

    def test_absurd_ttl_does_not_crash_and_is_bounded(self) -> None:
        # A huge ttl_days must not raise OverflowError from timedelta (days beyond
        # timedelta's ~1e9 limit). The grant is clamped to a sane maximum: never a
        # crash, never silently turned into an eternal grant.
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need it")
        out = self.svc.approve_proposal(self.who("demo-sophie-curator"), pid, ttl_days=10 ** 9)
        self.assertEqual(out["status"], "approved")
        state = self.svc.proposal_state(pid)
        self.assertIn("grant_expires", state, "a bounded expiry must be stamped, not omitted")
        self.assertLess(state["grant_expires"], "3000-01-01T00:00:00Z", "expiry must be clamped, not astronomical")

    def test_curator_grant_keeps_personal_data_restricted(self) -> None:
        self._granted_pid(approver="demo-sophie-curator")
        # sales-confidential unblocked, but personal-data still restricted -> sanitized
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        self.assertEqual(self.brief_access("demo-broad-viewer"), "sanitized")

    def test_admin_grant_unblocks_personal_data(self) -> None:
        self._granted_pid(approver="demo-ada-admin")
        # admin grant covers personal-data too -> nothing left restricted -> allowed
        self.assertEqual(self.brief_access("demo-broad-viewer"), "allowed")

    def test_explicit_ttl_stamps_grant_expiry(self) -> None:
        # approver-chosen TTL must land on the grant, not the 30-day default
        pid = self._granted_pid(ttl_days=7)
        state = self.svc.proposal_state(pid)
        self.assertEqual(state.get("grant_expires"), "2026-06-21T00:00:00Z")

    def _run_worker(self) -> dict:
        """Apply approved proposals through the real single-writer worker."""
        return worker.apply_approved(
            self.vault, self.tmp / "proposals.jsonl", self.tmp / "audit.jsonl",
            self.tmp / "runtime", now=lambda: self.clock["t"],
        )

    def test_worker_apply_does_not_kill_the_grant(self) -> None:
        # The worker flips 'approved' -> 'applied' (its card-write is by design);
        # the access grant must stay alive until TTL expiry or explicit revoke.
        pid = self._granted_pid()
        summary = self._run_worker()
        self.assertIn(pid, summary["applied"])
        self.assertEqual(self.svc.proposal_state(pid).get("status"), "applied")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")

    def test_revoke_works_after_worker_apply(self) -> None:
        pid = self._granted_pid()
        self._run_worker()
        out = self.svc.revoke_proposal(self.who("demo-sophie-curator"), pid, "no longer needed")
        self.assertEqual(out["status"], "revoked")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")

    def test_applied_grant_still_expires(self) -> None:
        self._granted_pid(ttl_days=1)  # expires 2026-06-15
        self._run_worker()
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        self.clock["t"] = "2026-06-16T00:00:00Z"  # past expiry
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")

    def test_tampered_expiry_drops_live_access(self) -> None:
        # A grant_expires corrupted in the log must fail CLOSED: the grant is
        # dropped, never turned into an eternal grant with time filtering off.
        pid = self._granted_pid()
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        ProposalStore(self.tmp / "proposals.jsonl").append_status(pid, {"grant_expires": "not-a-timestamp"})
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")


class GrantExpiryFailClosed(unittest.TestCase):
    """FINDING 1: an unparseable grant_expires must reject the grant (fail closed);
    an unparseable `now` stub only disables the time filter (fail soft for tests)."""

    def setUp(self) -> None:
        self.store = ProposalStore(Path(tempfile.mkdtemp(prefix="grant-exp-")) / "proposals.jsonl")

    def _grant(self, expires: str | None) -> None:
        record = {"type": "request_access", "status": "approved",
                  "requester": "demo-broad-viewer", "target": "demo-company-x"}
        if expires is not None:
            record["grant_expires"] = expires
        self.store.append(record)

    def test_malformed_expiry_makes_grant_inactive(self) -> None:
        self._grant("garbage-not-a-date")
        self.assertEqual(self.store.active_grants(now="2026-06-14T00:00:00Z"), set())

    def test_malformed_expiry_is_inactive_even_without_now(self) -> None:
        # Fail closed regardless of whether a cutoff clock is supplied.
        self._grant("garbage-not-a-date")
        self.assertEqual(self.store.active_grants(), set())

    def test_unparseable_now_stub_skips_time_filter_for_valid_expiry(self) -> None:
        self._grant("2099-01-01T00:00:00Z")
        self.assertIn(("demo-broad-viewer", "demo-company-x", "sales-confidential"),
                      self.store.active_grants(now="t"))

    def test_grant_without_expiry_stays_active(self) -> None:
        # Stub-clock approvals record no expiry (documented); the grant stays live
        # until an explicit revoke/reject.
        self._grant(None)
        self.assertIn(("demo-broad-viewer", "demo-company-x", "sales-confidential"),
                      self.store.active_grants(now="2026-06-14T00:00:00Z"))


class StubClockApproval(unittest.TestCase):
    """FINDING 2: approving a request_access under a non-ISO now() stub must not
    crash between the audit record and the status append. The expiry is computed
    up front; an unparseable now yields a grant WITHOUT grant_expires (consistent
    with the store's fail-soft handling of an unparseable cutoff clock)."""

    def setUp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="stub-approve-"))
        vault = tmp / "vault"
        vault.mkdir()
        self.svc = build_default_service(vault, tmp / "audit.jsonl", tmp / "proposals.jsonl", now=lambda: "t")

    def who(self, actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def test_stub_clock_approve_does_not_crash_or_strand_the_draft(self) -> None:
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need it")
        out = self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)
        self.assertEqual(out["status"], "approved")
        state = self.svc.proposal_state(pid)
        self.assertEqual(state.get("status"), "approved", "no half-recorded state: the status append must land")
        self.assertNotIn("grant_expires", state, "an unparseable now must not stamp a bogus expiry")


if __name__ == "__main__":
    unittest.main()
