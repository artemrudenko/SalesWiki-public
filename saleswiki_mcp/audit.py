"""Append-only, tamper-evident audit sink (JSONL).

Each record carries a `prev` hash and a `hash` over (prev + its content), forming
a chain: altering or removing an *interior* record, or corrupting any line, breaks
a later hash (or fails to parse), so `verify_chain` catches it. Appends are
flock-serialized (via the jsonl helper). Git records what changed; this records
who accessed/decided what.

Honest limit: truncating the *newest* records leaves a shorter but internally
consistent chain, so tail truncation is only detectable against an external
anchor — pass `expected_count` (e.g. a count snapshotted elsewhere or a
git-committed copy) to `verify_chain`. This is tamper-evidence, not
tamper-prevention.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path

from . import jsonl


def _hash(prev: str, event: dict) -> str:
    payload = json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()


class AuditAnchorError(ValueError):
    """Raised when a signed audit checkpoint cannot be trusted."""


def _read_chain(path: Path) -> list[dict] | None:
    """Return verified records, or ``None`` when the chain is malformed."""
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            return None
    prev = ""
    for record in records:
        content = {k: v for k, v in record.items() if k not in ("prev", "hash")}
        if record.get("prev") != prev or record.get("hash") != _hash(prev, content):
            return None
        prev = record["hash"]
    return records


class AuditSink:
    def __init__(self, path: Path | None) -> None:
        self._path = Path(path) if path else None

    def record(self, event: dict) -> None:
        if self._path is None:
            return
        # Read-last-hash and append happen under one lock (jsonl.append_computed)
        # so concurrent writers cannot both chain off the same `prev` and silently
        # break the tamper-evident chain.
        def chain(records: list[dict]) -> dict:
            prev = records[-1].get("hash", "") if records else ""
            return {**event, "prev": prev, "hash": _hash(prev, event)}

        jsonl.append_computed(self._path, chain)


def verify_chain(path: Path, expected_count: int | None = None) -> bool:
    """Return True iff the audit hash-chain is intact. Detects any interior edit or
    deletion and any corrupted/torn line (an unparseable line fails instead of being
    silently skipped). Tail truncation of the newest records is only detectable when
    `expected_count` is supplied — the surviving prefix is otherwise self-consistent.
    """
    records = _read_chain(Path(path))
    if records is None:
        return False
    if expected_count is not None and len(records) != expected_count:
        return False
    return True


def _anchor_payload(count: int, head_hash: str) -> dict[str, int | str]:
    return {"version": 1, "count": count, "head_hash": head_hash}


def _anchor_signature(payload: dict[str, int | str], key: bytes) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


def _write_anchor(destination: Path, anchor: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        handle.write(json.dumps(anchor, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, destination)


def create_anchor(audit_path: Path, anchor_path: Path, key: bytes) -> dict:
    """Create a signed checkpoint for a verified audit prefix.

    Keep ``anchor_path`` outside the audit runtime volume and keep ``key`` in a
    secret manager. The checkpoint makes deletion or rewriting of the protected
    prefix detectable, while allowing new audit events to be appended later.
    """
    records = _read_chain(Path(audit_path))
    if records is None:
        raise AuditAnchorError("audit chain is invalid; refusing to anchor it")
    payload = _anchor_payload(len(records), records[-1]["hash"] if records else "")
    anchor = {**payload, "signature": _anchor_signature(payload, key)}
    destination = Path(anchor_path)
    if destination.exists():
        raise AuditAnchorError("checkpoint already exists; verify it and use advance instead")
    _write_anchor(destination, anchor)
    return payload


def verify_anchor(audit_path: Path, anchor_path: Path, key: bytes) -> bool:
    """Verify the current log and a signed checkpoint held outside its volume."""
    try:
        anchor = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
        payload = _anchor_payload(int(anchor["count"]), str(anchor["head_hash"]))
        signature = str(anchor["signature"])
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    if not hmac.compare_digest(signature, _anchor_signature(payload, key)):
        return False
    records = _read_chain(Path(audit_path))
    if records is None or len(records) < payload["count"]:
        return False
    if payload["count"] == 0:
        return payload["head_hash"] == ""
    return records[payload["count"] - 1].get("hash") == payload["head_hash"]


def advance_anchor(audit_path: Path, anchor_path: Path, key: bytes) -> dict:
    """Advance an existing checkpoint only after it has verified cleanly."""
    destination = Path(anchor_path)
    if not destination.exists():
        raise AuditAnchorError("checkpoint does not exist; create the bootstrap anchor first")
    if not verify_anchor(audit_path, destination, key):
        raise AuditAnchorError("existing checkpoint does not verify; refusing to replace it")
    records = _read_chain(Path(audit_path))
    if records is None:  # Defensive: verification above already established this.
        raise AuditAnchorError("audit chain became invalid while advancing checkpoint")
    payload = _anchor_payload(len(records), records[-1]["hash"] if records else "")
    _write_anchor(destination, {**payload, "signature": _anchor_signature(payload, key)})
    return payload
