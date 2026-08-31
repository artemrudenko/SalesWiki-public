"""Single-writer worker: the only component that writes production cards.

It applies *approved* proposals from the append-only proposal store, after
validating the payload hash and the base card version, while holding a
single-writer lock. Every applied change is a bullet appended to the target
card's Review Needed section; the proposal status is advanced append-only and an
audit event is recorded. Any validation failure or a held lock leaves production
unchanged. The MCP gateway never imports this module - it is read/propose only.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from . import config, frontmatter, signing
from .audit import AuditSink
from .formatter import add_bullet_to_section, remove_lines_containing
from .proposals import ProposalStore, content_hash, payload_hash
from .retrieval import Retriever

LOCK_NAME = ".worker.lock"
DLQ_NAME = "dlq.jsonl"


def _default_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextlib.contextmanager
def _single_writer(lock_path: Path) -> Iterator[bool]:
    """Hold an advisory single-writer lock. Yields True if acquired. Uses
    fcntl.flock so the OS releases it automatically if the process crashes -
    no stale lock file can deadlock the worker."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _default_validate(text: str) -> bool:
    """Post-apply sanity check: frontmatter still parses and the section we
    appended to is still present. Stands in for a full health check.
    """
    props, _ = frontmatter.parse(text)
    return bool(props) and "## Review Needed" in text


def dead_letters(runtime_dir) -> list[dict]:
    """Read the dead-letter queue: proposals that failed to apply safely."""
    path = Path(runtime_dir) / DLQ_NAME
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def apply_approved(
    vault_root,
    proposal_path,
    audit_path,
    runtime_dir,
    now: Callable[[], str] | None = None,
    validate: Callable[[str], bool] | None = None,
) -> dict:
    """Apply every approved-but-unapplied proposal. Returns a run summary.

    `validate` checks the candidate (post-apply) card content in memory before it
    is written; a failure dead-letters the proposal and never writes it (no revert
    needed — defaults to a frontmatter + section check).
    """
    now = now or _default_now
    validate = validate or _default_validate
    vault_root = Path(vault_root)
    runtime_dir = Path(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lock_path = runtime_dir / LOCK_NAME

    summary: dict = {"locked": False, "applied": [], "failed": [], "dead_letter": []}

    store = ProposalStore(Path(proposal_path))
    audit = AuditSink(Path(audit_path))
    retriever = Retriever(vault_root, config.boundary_registry())
    # The approval key lives beside the proposal store (or an injected secret): the
    # worker applies only approvals it can verify, so a forged `approved` record is
    # dead-lettered instead of written to a card.
    approval_key = signing.resolve_key(Path(proposal_path).parent)
    # Single-writer lock (flock): refuse to run if another writer holds it.
    with _single_writer(lock_path) as acquired:
        if not acquired:
            summary["locked"] = True
            return summary
        for pid, state in store.states().items():
            if state.get("status") != "approved":
                continue
            failure = _validate_and_apply(vault_root, retriever, state, validate, approval_key)
            if failure is None:
                store.append_status(pid, {"event": "apply_result", "status": "applied", "applied": now(), "applied_by": "worker"})
                _audit(audit, now, state, "applied", "approved proposal applied to Review Needed", pid)
                summary["applied"].append(pid)
            else:
                store.append_status(pid, {"event": "apply_result", "status": "failed", "failed": now(), "reason": failure})
                _audit(audit, now, state, "failed", failure, pid)
                _dead_letter(runtime_dir, now, state, failure)
                summary["failed"].append({"proposal_id": pid, "reason": failure})
                summary["dead_letter"].append({"proposal_id": pid, "reason": failure})
    return summary


def _flag_bullet(state: dict) -> str:
    return f"{state.get('approved', '')} flag: {state.get('note', '')} (proposal {state['proposal_id']}, approved by {state.get('approver', 'unknown')})"


def _redaction_bullet(state: dict) -> str:
    return f"{state.get('approved', '')} Redaction review requested: {state.get('note', '')} (proposal {state['proposal_id']}, approved by {state.get('approver', 'unknown')})"


def _access_bullet(state: dict) -> str:
    return f"{state.get('approved', '')} Access requested: {state.get('note', '')} (proposal {state['proposal_id']}, requester {state.get('requester', 'unknown')} [{state.get('role', '')}], approved by {state.get('approver', 'unknown')})"


def _ingest_bullet(state: dict) -> str:
    return f"{state.get('approved', '')} 📥 Ingest proposed: {state.get('note', '')} (proposal {state['proposal_id']}, requester {state.get('requester', 'unknown')} [{state.get('role', '')}], approved by {state.get('approver', 'unknown')})"


# Maps a proposal type to the bullet it appends to the Review Needed section.
# Adding a new proposal type means adding one handler here.
_HANDLERS: dict[str, Callable[[dict], str]] = {
    "flag_stale_or_wrong": _flag_bullet,
    "request_redaction_review": _redaction_bullet,
    "request_access": _access_bullet,
    "ingest_resource": _ingest_bullet,
}


def _validate_and_apply(vault_root: Path, retriever: Retriever, state: dict, validate: Callable[[str], bool], approval_key: bytes) -> str | None:
    """Apply one proposal transactionally. Returns None on success or a failure
    reason string; the candidate content is validated in memory and written
    atomically only if valid, so a failure never writes (no revert window).
    """
    ptype = state.get("type", "")
    handler = _HANDLERS.get(ptype)
    if handler is None:
        return "unknown-proposal-type"

    # The approval must be signed by a key holder: a forged/tampered `approved`
    # record (e.g. an escalated approver_role) fails verification and is refused.
    if not signing.verify(approval_key, state):
        return "unsigned-or-invalid-approval"

    expected = payload_hash(ptype, state.get("target", ""), state.get("note", ""))
    if expected != state.get("payload_hash"):
        return "payload-hash-mismatch"

    card = retriever.find(state.get("target", ""))
    if card is None:
        return "target-not-found"

    path = vault_root / card.rel_path
    original = path.read_text(encoding="utf-8")
    bullet = handler(state)
    # Idempotency FIRST, before the base-version check: if this proposal's bullet
    # is already present (a crash after the atomic write but before the applied-
    # status append), the rerun is a no-op success. The bullet embeds the proposal
    # id, so it is unique. Checking base_hash first would instead dead-letter an
    # already-applied proposal, because the applied bullet (and any later edit)
    # moves the card body past the captured base_hash.
    if f"- {bullet}" in original:
        return None

    if state.get("base_hash") and content_hash(card.body) != state["base_hash"]:
        return "base-version-mismatch"

    updated = add_bullet_to_section(original, "Review Needed", bullet)
    # Validate the new content in memory BEFORE touching disk, then write
    # atomically (temp + os.replace) so a crash can never leave a half-applied
    # card and a rejected apply never writes at all (no revert window).
    if not validate(updated):
        return "post-apply-validation-failed"
    _atomic_write(path, updated)
    return None


def _atomic_write(path: Path, content: str) -> None:
    """Write via a temp file in the same directory + os.replace, so the card is
    never observed half-written and a crash leaves either the old or new file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def rollback(
    vault_root,
    proposal_path,
    audit_path,
    runtime_dir,
    proposal_id: str,
    now: Callable[[], str] | None = None,
) -> dict:
    """Undo an applied proposal: remove its Review Needed bullet and mark it
    rolled-back. Single-writer, append-only, idempotent.
    """
    now = now or _default_now
    vault_root = Path(vault_root)
    runtime_dir = Path(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lock_path = runtime_dir / LOCK_NAME

    store = ProposalStore(Path(proposal_path))
    audit = AuditSink(Path(audit_path))
    retriever = Retriever(vault_root, config.boundary_registry())
    with _single_writer(lock_path) as acquired:
        if not acquired:
            return {"locked": True, "status": "locked"}
        state = store.state(proposal_id)
        if state.get("status") != "applied":
            return {"locked": False, "status": "noop"}
        card = retriever.find(state.get("target", ""))
        if card is None:
            # Do NOT mark the proposal rolled-back when the card cannot be found
            # (deleted, renamed, or an ambiguous target): that would append an
            # append-only 'rolled-back' status the noop guard then makes unretryable,
            # leaving the applied bullet live while the ledger claims it was undone.
            _audit(audit, now, state, "target-not-found", "rollback could not resolve the target card", proposal_id, tool="worker_rollback")
            return {"locked": False, "status": "target-not-found"}
        path = vault_root / card.rel_path
        cleaned = remove_lines_containing(path.read_text(encoding="utf-8"), f"(proposal {proposal_id},")
        _atomic_write(path, cleaned)
        store.append_status(proposal_id, {"event": "rollback_result", "status": "rolled-back", "rolled_back": now()})
        _audit(audit, now, state, "rolled-back", "applied proposal rolled back", proposal_id, tool="worker_rollback")
        return {"locked": False, "status": "rolled-back"}


def _dead_letter(runtime_dir: Path, now, state: dict, reason: str) -> None:
    record = {
        "proposal_id": state.get("proposal_id", ""),
        "type": state.get("type", ""),
        "target": state.get("target", ""),
        "reason": reason,
        "dead_lettered": now(),
    }
    with (runtime_dir / DLQ_NAME).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _audit(audit: AuditSink, now, state: dict, decision: str, reason: str, pid: str, tool: str = "worker_apply") -> None:
    audit.record(
        {
            "timestamp": now(),
            "actor": "worker",
            "role": "worker",
            "tool": tool,
            "resource": state.get("target", ""),
            "decision": decision,
            "reason": reason,
            "proposal_id": pid,
        }
    )


def main() -> int:
    root = Path(os.environ.get("SALESWIKI_VAULT_ROOT", str(Path(__file__).resolve().parents[1] / "demo" / "permissioned")))
    runtime = Path(os.environ.get("SALESWIKI_RUNTIME_DIR", str(Path(__file__).resolve().parents[1] / "demo" / "runtime")))
    summary = apply_approved(root, runtime / "proposals.jsonl", runtime / "audit.jsonl", runtime)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
