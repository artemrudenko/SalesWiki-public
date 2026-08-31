"""Slice 5 tests: rollback of an applied proposal.

Rollback is the inverse of apply: under the single-writer lock it removes the
bullet the worker added to the Review Needed section, advances the proposal
status to rolled-back (append-only) and audits it. It is idempotent and safe on
proposals that were never applied.
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


class WorkerRollback(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="rollback-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.proposals = self.tmp / "proposals.jsonl"
        self.audit = self.tmp / "audit.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(self.vault, self.audit, self.proposals, now=lambda: "t")
        self.pid = self.svc.flag_stale_or_wrong(actor("demo-ivan-ae"), TARGET, "pricing looks stale")
        self.svc.approve_proposal(actor("demo-marina-curator"), self.pid)
        self.card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"
        self.before_apply = self.card.read_bytes()
        worker.apply_approved(self.vault, self.proposals, self.audit, self.runtime, now=lambda: "t2")

    def _rollback(self):
        return worker.rollback(self.vault, self.proposals, self.audit, self.runtime, self.pid, now=lambda: "t3")

    def test_rollback_removes_the_applied_note(self) -> None:
        self.assertIn("pricing looks stale", self.card.read_text(encoding="utf-8"))
        result = self._rollback()
        self.assertEqual(result["status"], "rolled-back")
        self.assertNotIn("pricing looks stale", self.card.read_text(encoding="utf-8"))
        self.assertEqual(self.svc.proposal_state(self.pid)["status"], "rolled-back")

    def test_rollback_restores_original_content(self) -> None:
        self._rollback()
        self.assertEqual(self.card.read_bytes(), self.before_apply, "rollback must restore the pre-apply card")

    def test_rollback_is_idempotent(self) -> None:
        self._rollback()
        result = self._rollback()
        self.assertEqual(result["status"], "noop")

    def test_rollback_records_audit(self) -> None:
        self._rollback()
        events = [json.loads(l) for l in self.audit.read_text().splitlines() if l.strip()]
        self.assertTrue(any(e["tool"] == "worker_rollback" for e in events))

    def test_rollback_respects_single_writer_lock(self) -> None:
        import fcntl
        import os
        self.runtime.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.runtime / ".worker.lock", os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)  # another writer holds the lock
        try:
            result = self._rollback()
            self.assertTrue(result["locked"])
            self.assertIn("pricing looks stale", self.card.read_text(encoding="utf-8"))
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


if __name__ == "__main__":
    unittest.main()
