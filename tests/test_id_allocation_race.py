"""Id minting must be atomic per natural key (security review #9).

IdAllocator.mint read the ledger (lookup + known-id set) outside the lock that
its append took, so two concurrent mints of the same natural key both missed and
both appended — two ids for one real entity (the ledger is meant to BE the dedup
authority). The two sibling append sites (proposals, audit) already route their
read-decide-append through jsonl.append_computed under one lock; mint must too.
"""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp import jsonl  # noqa: E402
from saleswiki_mcp.ids import IdAllocator  # noqa: E402


class MintConcurrency(unittest.TestCase):
    def test_concurrent_same_natural_key_mints_exactly_one_id(self) -> None:
        ledger = Path(tempfile.mkdtemp(prefix="id-race-")) / "id-ledger.jsonl"
        alloc = IdAllocator(ledger)
        n = 16
        barrier = threading.Barrier(n)
        results: list[str | None] = [None] * n

        def worker(i: int) -> None:
            barrier.wait()  # release all threads together to maximize overlap
            results[i] = alloc.mint("company", natural_key="acme.com")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        records = jsonl.read_records(ledger)
        self.assertEqual(len(records), 1, "the same natural key must mint exactly one ledger record")
        self.assertEqual(len(set(results)), 1, "all concurrent minters must receive the same id")

    def test_reuse_is_idempotent_and_does_not_grow_the_ledger(self) -> None:
        ledger = Path(tempfile.mkdtemp(prefix="id-reuse-")) / "id-ledger.jsonl"
        alloc = IdAllocator(ledger)
        first = alloc.mint("company", natural_key="acme.com")
        again = alloc.mint("company", natural_key="acme.com")
        self.assertEqual(first, again)
        self.assertEqual(len(jsonl.read_records(ledger)), 1, "reuse must not append a duplicate record")


if __name__ == "__main__":
    unittest.main()
