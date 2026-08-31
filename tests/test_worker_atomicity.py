"""Worker apply is atomic and idempotent on the empty-base_hash path (review L1).

Two robustness properties:
1. A re-run after the bullet was already written (e.g. a crash between the
   atomic write and marking the proposal applied) must NOT append the bullet a
   second time — even when base_hash is empty (target card did not exist at
   capture time), where the base-version check is skipped.
2. A failed post-apply validation leaves the card byte-exact unchanged (the new
   content is validated before it is ever written to disk).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config, signing, worker  # noqa: E402
from saleswiki_mcp.proposals import payload_hash  # noqa: E402
from saleswiki_mcp.retrieval import Retriever  # noqa: E402

TARGET = "demo-company-bluepeak-energy"
KEY = b"k" * 32


class WorkerAtomicity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="worker-atom-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.retriever = Retriever(self.vault, config.boundary_registry())
        self.card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"

    def _state(self) -> dict:
        note = "pricing looks stale"
        state = {
            "type": "flag_stale_or_wrong",
            "target": TARGET,
            "note": note,
            "proposal_id": "p-empty-base",
            "approved": "t",
            "approver": "demo-marina-curator",
            "approver_role": "curator",
            "payload_hash": payload_hash("flag_stale_or_wrong", TARGET, note),
            "base_hash": "",  # card did not exist at capture time
        }
        state[signing.SIG_FIELD] = signing.sign(KEY, state)
        return state

    def test_rerun_with_empty_base_hash_does_not_double_apply(self) -> None:
        state = self._state()
        first = worker._validate_and_apply(self.vault, self.retriever, state, lambda _t: True, KEY)
        self.assertIsNone(first, "first apply should succeed")
        # Simulate a crash-rerun: the proposal is applied again with empty base_hash.
        second = worker._validate_and_apply(self.vault, self.retriever, state, lambda _t: True, KEY)
        self.assertIsNone(second, "rerun should be an idempotent no-op, not a failure")
        body = self.card.read_text(encoding="utf-8")
        self.assertEqual(body.count("proposal p-empty-base"), 1, "bullet must appear exactly once")

    def test_failed_validation_writes_nothing(self) -> None:
        before = self.card.read_bytes()
        failure = worker._validate_and_apply(self.vault, self.retriever, self._state(), lambda _t: False, KEY)
        self.assertEqual(failure, "post-apply-validation-failed")
        self.assertEqual(self.card.read_bytes(), before, "a rejected apply must not touch the card")


if __name__ == "__main__":
    unittest.main()
