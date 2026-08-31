"""Slice 9 tests: Curator/RevOps governance inbox over the proposal store.

review_queue and get_proposal are visible to reviewer roles (curator/HoS/RevOps/
admin); reject_proposal is an approver-only decision (curator/HoS/admin), so
RevOps can inspect the queue but not decide. All transitions are append-only and
never mutate production cards; a rejected proposal is never applied by the worker.
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
from saleswiki_mcp import config, worker  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

TARGET = "demo-company-bluepeak-energy"


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class GovernanceInbox(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="inbox-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.proposals = self.tmp / "proposals.jsonl"
        self.audit = self.tmp / "audit.jsonl"
        self.svc = build_default_service(self.vault, self.audit, self.proposals, now=lambda: "t")
        self.pid = self.svc.flag_stale_or_wrong(actor("demo-ivan-ae"), TARGET, "pricing looks stale")

    # -- review_queue ------------------------------------------------------
    def test_reviewers_see_queue(self) -> None:
        for who in ("demo-marina-curator", "demo-elena-hos", "demo-raj-revops", "demo-ada-admin"):
            out = self.svc.review_queue(actor(who))
            self.assertEqual(out["access"], "allowed", who)
            self.assertIn(self.pid, out["text"], f"{who} should see the pending proposal")

    def test_non_reviewers_are_blocked_from_queue(self) -> None:
        for who in ("demo-broad-viewer", "demo-sam-sdr", "demo-nina-marketing", "demo-ivan-ae", "demo-lena-legal"):
            out = self.svc.review_queue(actor(who))
            self.assertEqual(out["access"], "blocked", who)
            self.assertFalse(out["can_decide"], who)

    def test_queue_returns_server_decision_capability(self) -> None:
        for who in ("demo-marina-curator", "demo-elena-hos", "demo-ada-admin"):
            self.assertTrue(self.svc.review_queue(actor(who))["can_decide"], who)
        self.assertFalse(self.svc.review_queue(actor("demo-raj-revops"))["can_decide"])

    # -- get_proposal ------------------------------------------------------
    def test_get_proposal_for_reviewer(self) -> None:
        out = self.svc.get_proposal(actor("demo-marina-curator"), self.pid)
        self.assertEqual(out["status"], "draft")
        self.assertEqual(out["proposal"]["requester"], "demo-ivan-ae")

    def test_get_proposal_unknown_is_safe(self) -> None:
        out = self.svc.get_proposal(actor("demo-marina-curator"), "proposal-9999")
        self.assertEqual(out["status"], "not-found")

    def test_get_proposal_blocked_for_non_reviewer(self) -> None:
        out = self.svc.get_proposal(actor("demo-nina-marketing"), self.pid)
        self.assertEqual(out["status"], "blocked")

    # -- reject_proposal ---------------------------------------------------
    def test_curator_can_reject_append_only_no_mutation(self) -> None:
        before_cards = {p: p.read_bytes() for p in self.vault.rglob("*.md")}
        lines_before = len(self.proposals.read_text().splitlines())
        result = self.svc.reject_proposal(actor("demo-marina-curator"), self.pid, "not a real issue")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.svc.proposal_state(self.pid)["status"], "rejected")
        self.assertEqual(len(self.proposals.read_text().splitlines()), lines_before + 1, "reject appends one record")
        for p, h in before_cards.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by reject")

    def test_revops_can_inspect_but_not_reject(self) -> None:
        out = self.svc.reject_proposal(actor("demo-raj-revops"), self.pid, "x")
        self.assertEqual(out["status"], "blocked", "RevOps inspects but does not decide")
        self.assertEqual(self.svc.proposal_state(self.pid)["status"], "draft")

    def test_rejected_proposal_is_never_applied(self) -> None:
        self.svc.reject_proposal(actor("demo-marina-curator"), self.pid, "no")
        summary = worker.apply_approved(self.vault, self.proposals, self.audit, self.tmp / "runtime", now=lambda: "t2")
        self.assertNotIn(self.pid, summary["applied"])

    def test_audit_records_governance(self) -> None:
        self.svc.review_queue(actor("demo-marina-curator"))
        self.svc.reject_proposal(actor("demo-marina-curator"), self.pid, "no")
        events = [json.loads(l) for l in self.audit.read_text().splitlines() if l.strip()]
        tools = {e["tool"] for e in events}
        self.assertIn("review_queue", tools)
        self.assertIn("reject_proposal", tools)


if __name__ == "__main__":
    unittest.main()
