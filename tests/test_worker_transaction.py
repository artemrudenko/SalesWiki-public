"""Slice 5 tests: transactional apply + dead-letter queue.

If the post-apply validation fails, the worker reverts the card to its exact
pre-apply content (production unchanged) and dead-letters the proposal. Terminal
validation failures (payload/base/unknown-type) are also dead-lettered for
operator review.
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


class WorkerTransaction(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="worker-txn-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.proposals = self.tmp / "proposals.jsonl"
        self.audit = self.tmp / "audit.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(self.vault, self.audit, self.proposals, now=lambda: "t")
        self.pid = self.svc.flag_stale_or_wrong(actor("demo-ethan-ae"), TARGET, "pricing looks stale")
        self.svc.approve_proposal(actor("demo-sophie-curator"), self.pid)
        self.card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"

    def test_post_apply_validation_failure_reverts_card(self) -> None:
        before = self.card.read_bytes()
        summary = worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "t2", validate=lambda text: False,
        )
        self.assertEqual(summary["applied"], [])
        self.assertEqual(self.card.read_bytes(), before, "failed validation must revert the card exactly")
        self.assertTrue(summary["dead_letter"], "a reverted apply must be dead-lettered")

    def test_dead_letter_file_records_terminal_failures(self) -> None:
        worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "t2", validate=lambda text: False,
        )
        dlq = worker.dead_letters(self.runtime)
        self.assertTrue(any(d["proposal_id"] == self.pid for d in dlq))
        self.assertTrue(all("reason" in d for d in dlq))

    def test_successful_apply_writes_no_dead_letter(self) -> None:
        summary = worker.apply_approved(self.vault, self.proposals, self.audit, self.runtime, now=lambda: "t2")
        self.assertIn(self.pid, summary["applied"])
        self.assertEqual(summary["dead_letter"], [])
        self.assertEqual(worker.dead_letters(self.runtime), [])

    def test_default_validation_accepts_a_normal_apply(self) -> None:
        # No injected validator: the default validator (frontmatter + section
        # intact) must accept the real apply.
        summary = worker.apply_approved(self.vault, self.proposals, self.audit, self.runtime, now=lambda: "t2")
        self.assertIn(self.pid, summary["applied"])
        self.assertEqual(self.svc.proposal_state(self.pid)["status"], "applied")


if __name__ == "__main__":
    unittest.main()
