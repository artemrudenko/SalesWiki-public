"""Slice 4 tests: single-writer worker apply path.

The worker is the only component that writes production cards. It applies only
approved proposals, validates the payload hash and base version, holds a
single-writer lock, appends to the card's Review Needed section, and updates the
proposal status - all append-only and audited. Any validation failure or a held
lock must leave production unchanged.
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


class WorkerApply(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="worker-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.proposals = self.tmp / "proposals.jsonl"
        self.audit = self.tmp / "audit.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(self.vault, self.audit, self.proposals, now=lambda: "2026-06-03T00:00:00Z")
        self.pid = self.svc.flag_stale_or_wrong(actor("demo-ethan-ae"), TARGET, "pricing looks stale")
        self.card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"

    def _run(self):
        return worker.apply_approved(
            vault_root=self.vault,
            proposal_path=self.proposals,
            audit_path=self.audit,
            runtime_dir=self.runtime,
            now=lambda: "2026-06-03T01:00:00Z",
        )

    def _approve(self):
        self.svc.approve_proposal(actor("demo-sophie-curator"), self.pid)

    def test_approved_proposal_is_applied(self) -> None:
        self._approve()
        summary = self._run()
        self.assertIn(self.pid, summary["applied"])
        text = self.card.read_text(encoding="utf-8")
        self.assertIn("pricing looks stale", text)
        self.assertIn(self.pid, text)
        self.assertIn("## Review Needed", text)
        self.assertEqual(self.svc.proposal_state(self.pid)["status"], "applied")

    def test_unapproved_proposal_is_not_applied(self) -> None:
        before = self.card.read_bytes()
        summary = self._run()
        self.assertEqual(summary["applied"], [])
        self.assertEqual(self.card.read_bytes(), before, "draft proposal must not touch production")

    def test_payload_hash_mismatch_blocks_apply(self) -> None:
        self._approve()
        before = self.card.read_bytes()
        # Tamper: append a record that changes the note after approval.
        with self.proposals.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"proposal_id": self.pid, "note": "DELETE the whole card"}) + "\n")
        summary = self._run()
        self.assertEqual(summary["applied"], [])
        self.assertTrue(any(f["proposal_id"] == self.pid for f in summary["failed"]))
        self.assertEqual(self.card.read_bytes(), before, "tampered payload must not be applied")

    def test_base_version_mismatch_blocks_apply(self) -> None:
        self._approve()
        # The target card changed since the proposal was drafted.
        self.card.write_text(self.card.read_text(encoding="utf-8") + "\n<!-- edited elsewhere -->\n", encoding="utf-8")
        summary = self._run()
        self.assertEqual(summary["applied"], [])
        self.assertNotIn("pricing looks stale", self.card.read_text(encoding="utf-8"))

    def test_single_writer_lock_prevents_apply(self) -> None:
        import fcntl
        import os
        self._approve()
        before = self.card.read_bytes()
        self.runtime.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.runtime / ".worker.lock", os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)  # another writer holds the lock
        try:
            summary = self._run()
            self.assertTrue(summary["locked"])
            self.assertEqual(summary["applied"], [])
            self.assertEqual(self.card.read_bytes(), before)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def test_apply_is_idempotent(self) -> None:
        self._approve()
        self._run()
        summary2 = self._run()
        self.assertEqual(summary2["applied"], [], "an applied proposal must not re-apply")
        self.assertEqual(self.card.read_text(encoding="utf-8").count("pricing looks stale"), 1)

    def test_audit_records_apply(self) -> None:
        self._approve()
        self._run()
        events = [json.loads(l) for l in self.audit.read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "worker_apply" and e["decision"] == "applied" for e in events))


if __name__ == "__main__":
    unittest.main()
