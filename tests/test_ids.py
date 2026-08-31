"""Identifier-strategy tests: typed opaque ULID ids + natural-key dedup + ledger.

Ids are minted once at creation, never derived from mutable data (rename-safe),
are globally unique without coordination (opaque ULID core), time-sortable, and
idempotent per natural key so re-ingesting the same real object reuses its id.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp.ids import IdAllocator, ulid  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9-]+_[0-9A-HJKMNP-TV-Z]{26}$")


class UlidEncoding(unittest.TestCase):
    def test_ulid_is_26_crockford_chars(self) -> None:
        u = ulid(1_700_000_000_000, 12345)
        self.assertEqual(len(u), 26)
        self.assertRegex(u, r"^[0-9A-HJKMNP-TV-Z]{26}$")

    def test_ulid_is_time_sortable(self) -> None:
        earlier = ulid(1_700_000_000_000, 0)
        later = ulid(1_700_000_001_000, 0)
        self.assertLess(earlier, later)


class Allocator(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ids-"))
        self.ledger = self.tmp / "id-ledger.jsonl"
        self._t = 1_700_000_000_000
        self._r = 0

        def now_ms() -> int:
            self._t += 1000
            return self._t

        def randbits() -> int:
            self._r += 1
            return self._r

        self.alloc = IdAllocator(self.ledger, now_ms=now_ms, randbits=randbits)

    def test_minted_id_is_typed_and_well_formed(self) -> None:
        cid = self.alloc.mint("company")
        self.assertTrue(cid.startswith("company_"))
        self.assertRegex(cid, ID_RE)

    def test_no_natural_key_always_mints_new(self) -> None:
        a = self.alloc.mint("deal")
        b = self.alloc.mint("deal")
        self.assertNotEqual(a, b)

    def test_natural_key_is_idempotent(self) -> None:
        a = self.alloc.mint("company", natural_key="bluepeak.example")
        b = self.alloc.mint("company", natural_key="bluepeak.example")
        self.assertEqual(a, b, "same natural key must reuse the id (dedup)")

    def test_different_natural_keys_differ(self) -> None:
        a = self.alloc.mint("company", natural_key="a.example")
        b = self.alloc.mint("company", natural_key="b.example")
        self.assertNotEqual(a, b)

    def test_natural_key_is_scoped_by_type(self) -> None:
        c = self.alloc.mint("company", natural_key="acme")
        d = self.alloc.mint("deal", natural_key="acme")
        self.assertNotEqual(c, d, "same key under different types are different entities")

    def test_ids_are_time_sortable_in_mint_order(self) -> None:
        ids = [self.alloc.mint("lead") for _ in range(5)]
        self.assertEqual(ids, sorted(ids))

    def test_ledger_is_append_only_and_records_provenance(self) -> None:
        self.alloc.mint("company", natural_key="x.example")
        records = self.alloc.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "company")
        self.assertEqual(records[0]["natural_key"], "x.example")
        self.assertIn("minted", records[0])
        # Re-mint with the same key appends nothing new.
        self.alloc.mint("company", natural_key="x.example")
        self.assertEqual(len(self.alloc.records()), 1)


if __name__ == "__main__":
    unittest.main()


class LedgerHealthCheck(unittest.TestCase):
    """The health_check guard catches a corrupt/contradictory ledger."""

    def setUp(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import health_check  # noqa: E402
        self.hc = health_check
        self.tmp = Path(tempfile.mkdtemp(prefix="ledger-"))
        self.path = self.tmp / "id-ledger.jsonl"

    def _findings(self):
        out: list = []
        self.hc.check_id_ledger(out, path=self.path)
        return [f.message for f in out]

    def test_valid_ledger_passes(self) -> None:
        alloc = IdAllocator(self.path)
        alloc.mint("company", natural_key="a.example")
        alloc.mint("deal")
        self.assertEqual(self._findings(), [])

    def test_absent_ledger_is_noop(self) -> None:
        self.assertEqual(self._findings(), [])

    def test_malformed_id_is_caught(self) -> None:
        self.path.write_text('{"id": "company-not-a-ulid", "type": "company"}\n', encoding="utf-8")
        self.assertTrue(any("typed-ULID scheme" in m for m in self._findings()))

    def test_duplicate_id_is_caught(self) -> None:
        good = f"company_{ulid(1_700_000_000_000, 1)}"
        self.path.write_text(f'{{"id": "{good}", "type": "company"}}\n{{"id": "{good}", "type": "company"}}\n', encoding="utf-8")
        self.assertTrue(any("duplicate id" in m for m in self._findings()))

    def test_natural_key_collision_is_caught(self) -> None:
        a = f"company_{ulid(1_700_000_000_000, 1)}"
        b = f"company_{ulid(1_700_000_000_000, 2)}"
        self.path.write_text(
            f'{{"id": "{a}", "type": "company", "natural_key": "acme"}}\n'
            f'{{"id": "{b}", "type": "company", "natural_key": "acme"}}\n',
            encoding="utf-8",
        )
        self.assertTrue(any("maps to two ids" in m for m in self._findings()))
