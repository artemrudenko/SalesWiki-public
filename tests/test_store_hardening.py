"""Arch #6/#8 tests: robust JSONL reads + tamper-evident audit chain.

A torn/malformed trailing line must not break a read (#6). The audit log is a
hash-chain: a clean log verifies, and altering any past record fails verification
(#8). The worker lock is exercised via fcntl.flock in the worker tests.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp import jsonl  # noqa: E402
from saleswiki_mcp.audit import AuditSink, verify_chain  # noqa: E402
from saleswiki_mcp.proposals import ProposalStore  # noqa: E402


class RobustJsonl(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jsonl-"))
        self.path = self.tmp / "log.jsonl"

    def test_malformed_trailing_line_is_skipped(self) -> None:
        jsonl.append_line(self.path, {"a": 1})
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write('{"a": 2, "b":\n')  # torn write
        jsonl.append_line(self.path, {"a": 3})
        records = jsonl.read_records(self.path)
        self.assertEqual([r["a"] for r in records], [1, 3])

    def test_proposal_store_tolerates_torn_line(self) -> None:
        store = ProposalStore(self.path)
        store.append({"type": "flag_stale_or_wrong", "status": "draft", "proposal_id": "proposal-0001"})
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write("{not json}\n")
        self.assertIn("proposal-0001", store.states())


class AuditChain(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="audit-"))
        self.path = self.tmp / "audit.jsonl"
        self.sink = AuditSink(self.path)

    def test_clean_chain_verifies(self) -> None:
        for i in range(3):
            self.sink.record({"tool": "company_brief", "decision": "allow", "n": i})
        self.assertTrue(verify_chain(self.path))
        records = jsonl.read_records(self.path)
        self.assertTrue(all("prev" in r and "hash" in r for r in records))
        self.assertEqual(records[1]["prev"], records[0]["hash"])

    def test_tampering_breaks_the_chain(self) -> None:
        for i in range(3):
            self.sink.record({"tool": "deal_risk", "decision": "allow", "n": i})
        records = jsonl.read_records(self.path)
        records[1]["decision"] = "block"  # alter a past record, keep its hash
        self.path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        self.assertFalse(verify_chain(self.path), "altered record must break the chain")

    def test_deleting_a_record_breaks_the_chain(self) -> None:
        for i in range(3):
            self.sink.record({"tool": "x", "n": i})
        records = jsonl.read_records(self.path)
        del records[1]
        self.path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        self.assertFalse(verify_chain(self.path))


if __name__ == "__main__":
    unittest.main()
