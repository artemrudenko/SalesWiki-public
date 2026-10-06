"""Concurrency-safe append-only JSONL helpers.

Appends are serialized with an advisory file lock (fcntl.flock) so concurrent
writers cannot interleave a half-written line, and reads tolerate a malformed
trailing line (e.g. a write torn by a crash) instead of failing the whole read.
"""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Callable


def _parse(text: str) -> list[dict]:
    """Parse JSONL text, skipping any line that does not parse (robust to a torn tail)."""
    records: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def append_line(path: Path, obj: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(line + "\n")
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_computed(path: Path, compute: Callable[[list[dict]], dict | None]) -> dict | None:
    """Atomic read-modify-append: under a single exclusive lock, read the existing
    records, call `compute(records)` to build the new record, then append it.

    Serializing the read and the write under one lock is what makes a chained
    append (e.g. an audit hash-chain whose `prev` depends on the last record)
    safe against concurrent writers — without it, two writers can read the same
    prior state and both append on top of it. `compute` may return None to append
    nothing (e.g. an idempotent mint whose natural key already exists); the return
    value (the appended record, or None) is passed back to the caller.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # "a+" keeps writes at EOF (append semantics) while still allowing a read.
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            obj = compute(_parse(handle.read()))
            if obj is not None:
                handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
                # Flush to disk BEFORE releasing the lock: otherwise the next
                # writer could acquire the lock and read stale on-disk content
                # (our write still buffered), then chain off the same `prev` and
                # break the chain.
                handle.flush()
                os.fsync(handle.fileno())
            return obj
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def read_records(path: Path) -> list[dict]:
    """Parse JSONL, skipping any line that does not parse (robust to a torn tail)."""
    path = Path(path)
    if not path.exists():
        return []
    return _parse(path.read_text(encoding="utf-8"))


def read_records_checked(path: Path) -> tuple[list[dict], bool]:
    """Parse JSONL and also report whether the file was fully intact.

    Returns (records, intact); `intact` is False if any non-empty line failed to
    parse. `read_records` silently tolerates a torn/corrupt line, which is right
    for informational logs but wrong for security state: a caller deriving active
    access grants must fail closed on a store it cannot fully read, because an
    unparseable line could be a tampered revoke whose silent loss would restore
    access.
    """
    path = Path(path)
    if not path.exists():
        return [], True
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    records = _parse("\n".join(lines))
    return records, len(records) == len(lines)
