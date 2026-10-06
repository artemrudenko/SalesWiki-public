"""Entity identifier allocation (identifier-strategy, variant C).

Ids are minted once, at creation, and never derived from mutable data (so they
survive renames). The core is a typed, opaque, time-sortable ULID
(`<type>_<26 Crockford base32>`): globally unique without coordination (no central
lock needed), and lexicographically sortable by creation time. A natural key
(domain, email, CRM id) makes minting idempotent - re-ingesting the same real
object reuses its id instead of creating a duplicate. Every mint is recorded in an
append-only ledger for provenance and uniqueness. See
wiki/processes/identifier-strategy.md.

The human-readable slug stays a separate field (and the filename); references
resolve by id first, then slug/alias. This module is the single mint chokepoint.
"""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Callable

from . import jsonl

# Crockford base32 (no I, L, O, U) - case-insensitive, human-safe, sortable.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def ulid(timestamp_ms: int, randomness: int) -> str:
    """A ULID: 48-bit ms timestamp (10 chars) + 80-bit randomness (16 chars)."""
    return _encode(timestamp_ms & ((1 << 48) - 1), 10) + _encode(randomness & ((1 << 80) - 1), 16)


class IdAllocator:
    """The single place ids are minted. Backed by an append-only ledger."""

    def __init__(
        self,
        ledger_path: Path,
        now_ms: Callable[[], int] | None = None,
        randbits: Callable[[], int] | None = None,
    ) -> None:
        self._path = Path(ledger_path)
        self._now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)
        self._randbits = randbits or (lambda: secrets.randbits(80))

    def records(self) -> list[dict]:
        return jsonl.read_records(self._path)

    @staticmethod
    def _find(records: list[dict], card_type: str, natural_key: str) -> str | None:
        """Existing id for a (type, natural_key) within `records`, or None."""
        if not natural_key:
            return None
        for record in records:
            if record.get("type") == card_type and record.get("natural_key") == natural_key:
                return record.get("id")
        return None

    def lookup(self, card_type: str, natural_key: str) -> str | None:
        """Return the existing id for a (type, natural_key), or None."""
        return self._find(self.records(), card_type, natural_key)

    def mint(self, card_type: str, natural_key: str = "", explicit_id: str | None = None) -> str:
        """Mint (or reuse, by natural key) an id for a new entity of `card_type`.

        `explicit_id` routes a caller-chosen id (curated data, migration, a human
        id) through the same chokepoint + ledger with the same dedup, instead of a
        generated ULID. Re-using an already-recorded id is idempotent.

        The natural-key lookup, the id-collision check and the ledger append all
        run under one exclusive lock (jsonl.append_computed), so two concurrent
        mints of the same natural key cannot both miss and both append a duplicate
        — the ledger is the dedup authority. `compute` returns None (no append)
        when an id is reused.
        """
        outcome: dict[str, str] = {}

        def compute(records: list[dict]) -> dict | None:
            existing = self._find(records, card_type, natural_key)
            if existing:
                outcome["id"] = existing
                return None
            known = {r.get("id") for r in records}
            if explicit_id is not None:
                if explicit_id in known:
                    outcome["id"] = explicit_id  # already recorded; idempotent
                    return None
                new_id = explicit_id
            else:
                new_id = f"{card_type}_{ulid(self._now_ms(), self._randbits())}"
                while new_id in known:  # astronomically unlikely; cheap to be certain
                    new_id = f"{card_type}_{ulid(self._now_ms(), self._randbits())}"
            outcome["id"] = new_id
            return {
                "id": new_id,
                "type": card_type,
                "natural_key": natural_key,
                "minted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        jsonl.append_computed(self._path, compute)
        return outcome["id"]
