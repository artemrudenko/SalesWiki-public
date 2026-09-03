"""Slice 4 tests: proposal approval lifecycle (gateway side, append-only).

A draft proposal can only be approved by an approver role (curator/HoS/admin);
approval is recorded append-only and never mutates production cards. The worker
(separate, single-writer) is what applies an approved proposal.
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

TARGET = "demo-company-bluepeak-energy"


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


class Approval(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="approval-"))
        self.svc = make_service(self.tmp)
        self.pid = self.svc.flag_stale_or_wrong(actor("demo-ethan-ae"), TARGET, "pricing looks stale")
        self.proposals = self.tmp / "proposals.jsonl"

    def _states(self):
        return [json.loads(l) for l in self.proposals.read_text().splitlines() if l.strip()]

    def test_draft_carries_payload_hash(self) -> None:
        draft = self._states()[0]
        self.assertEqual(draft["status"], "draft")
        self.assertTrue(draft.get("payload_hash"), "draft must carry a payload hash")

    def test_curator_can_approve(self) -> None:
        result = self.svc.approve_proposal(actor("demo-sophie-curator"), self.pid)
        self.assertEqual(result["status"], "approved")
        merged = self.svc.proposal_state(self.pid)
        self.assertEqual(merged["status"], "approved")
        self.assertEqual(merged["approver"], "demo-sophie-curator")

    def test_sales_owner_cannot_approve(self) -> None:
        result = self.svc.approve_proposal(actor("demo-ethan-ae"), self.pid)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.svc.proposal_state(self.pid)["status"], "draft", "rejected approval must leave draft")

    def test_approval_is_append_only_and_no_card_mutation(self) -> None:
        before_cards = {p: p.read_bytes() for p in (self.tmp / "permissioned").rglob("*.md")}
        before_lines = len(self._states())
        self.svc.approve_proposal(actor("demo-sophie-curator"), self.pid)
        self.assertEqual(len(self._states()), before_lines + 1, "approval appends one record")
        self.assertEqual(self._states()[0]["status"], "draft", "original draft line is untouched")
        for p, h in before_cards.items():
            self.assertEqual(p.read_bytes(), h, f"{p} mutated by approval")

    def test_unknown_proposal_is_safe(self) -> None:
        result = self.svc.approve_proposal(actor("demo-sophie-curator"), "proposal-9999")
        self.assertEqual(result["status"], "not-found")

    def test_audit_records_approval(self) -> None:
        self.svc.approve_proposal(actor("demo-sophie-curator"), self.pid)
        events = [json.loads(l) for l in (self.tmp / "audit.jsonl").read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "approve_proposal" and e["decision"] == "allow" for e in events))


if __name__ == "__main__":
    unittest.main()
