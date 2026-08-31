"""Append-only proposal store (JSONL).

Slice 1 captured drafts only. Slice 4 adds an approval + apply lifecycle: status
transitions (draft -> approved -> applied/failed) are *appended* as new records,
never edited in place, so the JSONL stays an immutable event log. The current
state of a proposal is the ordered merge of all records sharing its id.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import jsonl


def _parse_iso(value: str) -> datetime | None:
    """Parse an ISO timestamp; return None for anything unparseable. Callers must
    treat the two unparseable cases differently: a non-date `now` stub (tests use
    now=lambda: "t") only disables time filtering (fail soft), while a malformed
    stored `grant_expires` must reject the grant (fail closed) — it must never
    silently become an eternal grant."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def payload_hash(ptype: str, target: str, note: str) -> str:
    """Stable hash of a proposal payload; used to detect tampering before apply."""
    digest = hashlib.sha256(f"{ptype}\n{target}\n{note}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def content_hash(text: str) -> str:
    """Stable hash of card content; used for optimistic base-version checks."""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class ProposalStore:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def records(self) -> list[dict]:
        return jsonl.read_records(self._path)

    @staticmethod
    def _next_proposal_id(records: list[dict]) -> str:
        """Sequential per-proposal id (count distinct proposals, not log records),
        so ids stay proposal-0001, -0002, ... regardless of status events. Takes an
        already-read record list so the count and the append can share one lock."""
        existing = {r.get("proposal_id", "") for r in records}
        return f"proposal-{len(existing) + 1:04d}"

    def append(self, record: dict) -> str:
        """Append a proposal (minting an id if absent) under a single exclusive
        lock: the id count and the append happen atomically, so two processes
        sharing the store can never mint the same proposal-NNNN (a merged id would
        let one approval act on a different requester/target than was reviewed)."""
        def compute(records: list[dict]) -> dict:
            proposal_id = record.get("proposal_id") or self._next_proposal_id(records)
            return {**record, "proposal_id": proposal_id}

        written = jsonl.append_computed(self._path, compute)
        return written["proposal_id"]

    def append_status(self, proposal_id: str, fields: dict) -> None:
        """Append a status-transition record for an existing proposal."""
        self.append({**fields, "proposal_id": proposal_id})

    @staticmethod
    def _merge(records: list[dict]) -> dict[str, dict]:
        """Merge all records per proposal id in order; later records win."""
        merged: dict[str, dict] = {}
        for record in records:
            pid = record.get("proposal_id", "")
            merged[pid] = {**merged.get(pid, {}), **record}
        return merged

    def states(self) -> dict[str, dict]:
        """Current state per proposal (torn-tail tolerant, for informational reads)."""
        return self._merge(self.records())

    def state(self, proposal_id: str) -> dict:
        return self.states().get(proposal_id, {})

    # Statuses under which an approved access grant is still live. The worker
    # advances an approved request_access to 'applied' when it records the grant
    # on the card's Review Needed section — that must NOT terminate the grant;
    # only TTL expiry or an explicit revoke/reject may.
    GRANT_ACTIVE_STATUSES = ("approved", "applied")

    def active_grants(self, now: str | None = None, verify: Callable[[dict], bool] | None = None) -> set[tuple[str, str, str]]:
        """Active grants as {(requester, target, boundary)} triples, derived from
        approved (or worker-applied) request_access proposals. A grant covers
        `sales-confidential` always, and `personal-data` only when an admin
        approved it. A later rejected/revoked status drops the grant automatically
        (states() keeps the latest status); when `now` is given, expired grants
        are dropped too. Read fresh each call so an approval/revocation takes
        effect immediately.

        `verify`, when supplied, must return True for a trusted approval record;
        grants whose merged state fails it are dropped (fail closed) so a forged,
        unsigned `approved` line never unlocks a read. When supplied it also
        triggers a payload_hash re-derivation (below). It is optional so unit tests
        can exercise the expiry logic on hand-built records without a key.

        The grant log is read fail-closed: a torn/corrupt line drops ALL grants,
        because it could be a tampered revoke whose silent loss would restore
        access (unlike states(), which stays torn-tail tolerant for informational
        reads). Only the grant elevation overlay is withheld; base RBAC/ABAC reads
        are unaffected.

        Expiry handling is asymmetric by design: an unparseable `now` (stub
        clocks) skips time filtering, but an unparseable stored `grant_expires`
        drops the grant — fail closed, never an accidental eternal grant."""
        records, intact = jsonl.read_records_checked(self._path)
        if not intact:
            return set()  # cannot fully read the grant log: fail closed
        cutoff = _parse_iso(now) if now else None
        grants: set[tuple[str, str, str]] = set()
        for s in self._merge(records).values():
            if s.get("type") != "request_access" or s.get("status") not in self.GRANT_ACTIVE_STATUSES:
                continue
            if verify is not None:
                if not verify(s):
                    continue  # forged/tampered approval: fail closed
                # The signature binds payload_hash but the read path consumes the
                # live target/type; re-derive and cross-check them (as the worker
                # does at worker._validate_and_apply) so a post-signing target/type
                # swap cannot redirect the grant. Skipped when verify is None, where
                # hand-built test records carry no payload_hash.
                if payload_hash(s.get("type", ""), s.get("target", ""), s.get("note", "")) != s.get("payload_hash"):
                    continue
            raw_expiry = s.get("grant_expires", "")
            if raw_expiry:
                expires = _parse_iso(raw_expiry)
                if expires is None:
                    continue  # fail closed on a corrupted/tampered expiry
                if cutoff is not None and expires <= cutoff:
                    continue
            requester, target = s.get("requester", ""), s.get("target", "")
            boundaries = {"sales-confidential"}
            if s.get("approver_role") == "admin":
                boundaries.add("personal-data")
            for boundary in boundaries:
                grants.add((requester, target, boundary))
        return grants
