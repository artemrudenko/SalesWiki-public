"""Audit hash-chain must stay intact under concurrent writers (security review M1).

`AuditSink.record` does read-last-hash → compute → append. If that read-modify-
write is not held under a single lock, two concurrent writers can both read the
same `prev`, both append claiming it, and silently break the tamper-evident
chain — making a benign race indistinguishable from tampering. In RC_USE_MCP
mode a subprocess is spawned per call, all appending to one shared audit.jsonl,
so this is a real deployment condition, not a theoretical one.
"""

from __future__ import annotations

import multiprocessing
import tempfile
import unittest
from pathlib import Path

from saleswiki_mcp.audit import AuditSink, verify_chain


def _hammer(path_str: str, worker_id: int, count: int) -> None:
    """Append `count` records to the shared audit log from one process."""
    sink = AuditSink(Path(path_str))
    for i in range(count):
        sink.record({"actor": f"w{worker_id}", "op": "read", "seq": i})


class AuditConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="audit-conc-"))
        self.log = self.tmp / "audit.jsonl"

    def test_chain_intact_under_concurrent_writers(self) -> None:
        workers, per = 8, 40
        ctx = multiprocessing.get_context("spawn")
        procs = [
            ctx.Process(target=_hammer, args=(str(self.log), w, per))
            for w in range(workers)
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)

        from saleswiki_mcp import jsonl

        records = jsonl.read_records(self.log)
        self.assertEqual(
            len(records), workers * per,
            "a concurrent append was lost (read-modify-write not serialized)",
        )
        self.assertTrue(
            verify_chain(self.log),
            "concurrent writers broke the hash-chain (TOCTOU on prev)",
        )


if __name__ == "__main__":
    unittest.main()
