"""HMAC signatures on approval records.

The proposal store is an unsigned append-only log, so any process that can append a
line can forge an `approved` record — the single-writer worker would then write it
to a production card, and the live grant overlay would unlock reads for it.
Signing binds each approval to the security-relevant fields
(who approved, in what role, until when, over which proposal payload) with a key the
proposal store itself does not contain. The worker and the grant overlay verify the
signature and ignore anything that fails.

Key resolution, in order:
  1. `SALESWIKI_APPROVAL_KEY` (hex/opaque string) — the production path: inject it as
     a secret mounted only to the worker and the approval issuer, NOT onto the
     proposal-store volume, so a compromised read/propose gateway cannot sign.
  2. A per-runtime key file `<runtime>/.approval_key` (0600), created on first use —
     the demo convenience: real signing with zero configuration. It is co-located
     with the store, so it only raises the bar against a confined appender (a
     prompt-injected tool with a narrow write, another process without dir read);
     production must use option 1 for a true trust boundary.

`status` is deliberately NOT signed: the worker advances an approved proposal to
`applied`, which must not invalidate the signature. The active-status gate is
enforced separately by the caller.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

ENV_KEY = "SALESWIKI_APPROVAL_KEY"
KEY_FILE = ".approval_key"
SIG_FIELD = "approval_sig"
# Minimum trusted key length. A shorter (or empty) key file is a broken stub, not
# a real key, and signing under it would be forgeable — regenerate instead.
MIN_KEY_BYTES = 16
_KEY_BYTES = 32


def _write_key_atomic(path: Path) -> None:
    """Create a fresh random key at `path` atomically: write to a temp file, fsync,
    then os.replace. Avoids the 0-byte window of an open-then-write, so a crash can
    never leave an empty (guessable) key file behind."""
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.write(fd, os.urandom(_KEY_BYTES))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)

# Stable, security-relevant fields an approval commits to. Includes `requester`
# (the grant beneficiary) because it is NOT covered by payload_hash, so without
# it a post-signing swap to another user would keep a valid signature. `type` and
# `target` are bound via payload_hash, which the worker and the grant overlay
# re-derive and cross-check. Excludes `status` (mutates approved -> applied) and
# any mutable bookkeeping.
_SIGNED_FIELDS = ("proposal_id", "payload_hash", "requester", "approver", "approver_role", "approved", "grant_expires")


def resolve_key(runtime_dir) -> bytes:
    """Return the approval-signing key (see module docstring for precedence)."""
    env = os.environ.get(ENV_KEY, "").strip()
    if env:
        return env.encode("utf-8")
    path = Path(runtime_dir) / KEY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        if path.exists():
            key = path.read_bytes()
            if len(key) >= MIN_KEY_BYTES:
                return key
            # A truncated/empty key file (a pre-created stub, a torn create, a
            # failed copy) is not a trustworthy key — signing under it is
            # forgeable. Replace it atomically and re-read (fail closed).
            _write_key_atomic(path)
            return path.read_bytes()
        try:
            # O_EXCL so two processes racing the first-use creation don't clobber
            # each other; the loser re-reads the winner's key on the next pass.
            # fsync before close so the file is not observed empty by a racer.
            fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
            try:
                os.write(fd, os.urandom(_KEY_BYTES))
                os.fsync(fd)
            finally:
                os.close(fd)
            return path.read_bytes()
        except FileExistsError:
            continue
    return path.read_bytes()


def sign(key: bytes, record: dict) -> str:
    """HMAC-SHA256 over the canonical signed content of an approval record."""
    content = {field: record.get(field, "") for field in _SIGNED_FIELDS}
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify(key: bytes, record: dict) -> bool:
    """True iff `record` carries a signature matching its signed content under `key`.

    A missing signature is a failure (an unsigned approval is not trusted)."""
    provided = record.get(SIG_FIELD, "")
    if not provided:
        return False
    return hmac.compare_digest(provided, sign(key, record))
