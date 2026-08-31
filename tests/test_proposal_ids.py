"""Proposal ids must be sequential per proposal (0001, 0002, ...) regardless of
how many status/lifecycle records each proposal accrues."""
from __future__ import annotations
import sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saleswiki_mcp.proposals import ProposalStore  # noqa: E402


class SequentialIds(unittest.TestCase):
    def test_ids_are_sequential_across_status_events(self) -> None:
        store = ProposalStore(Path(tempfile.mkdtemp()) / "p.jsonl")
        pid1 = store.append({"type": "flag_stale_or_wrong", "status": "draft"})
        # Several lifecycle records for the first proposal:
        for ev in ("approved", "applied", "rolled-back"):
            store.append_status(pid1, {"event": "x", "status": ev})
        pid2 = store.append({"type": "flag_stale_or_wrong", "status": "draft"})
        self.assertEqual(pid1, "proposal-0001")
        self.assertEqual(pid2, "proposal-0002", "second proposal must be 0002, not record-count-based")


if __name__ == "__main__":
    unittest.main()
