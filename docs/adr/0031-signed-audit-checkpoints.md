---
status: Accepted
date: 2026-08-31
deciders: SalesWiki maintainers
---

# ADR-0031: Signed audit checkpoints outside the runtime volume

## Status

Accepted.

## Context

ADR-0015 established a race-safe, hash-chained JSONL audit log. It catches a
modified or removed interior event, but a clean deletion of the newest events
leaves a valid shorter chain. `verify_chain(..., expected_count=N)` can detect
that case only when a trusted count is held elsewhere.

The project needs a useful control for a private pilot without claiming to have
an immutable remote audit platform. A checkpoint kept in the same writable
runtime folder, or signed with a key stored beside it, would not add protection
against an actor who can rewrite the log.

## Decision

SalesWiki provides a signed checkpoint containing the audit record count and
head hash. `scripts/audit_anchor.py` creates, verifies and advances it using an
HMAC key from a deployment-only environment variable. The checkpoint path and
key must be outside the gateway and worker audit runtime volume.

An existing checkpoint must verify before `advance` can replace it. This makes a
verification failure an explicit operational event rather than an opportunity to
silently re-anchor a shortened log. Checkpoint replacement is atomic.

## Consequences

**Positive**

- Tail deletion below the last checkpoint, a rewritten protected prefix and a
  modified checkpoint fail verification without a database dependency.
- New events may be appended after a checkpoint; a scheduled job can verify and
  advance the protected prefix.
- The public repository stores no signing key or runtime checkpoint.

**Negative / trade-offs**

- This is tamper-evidence, not WORM storage. An actor with access to the audit
  log, checkpoint and HMAC key can still rewrite all three.
- A checkpoint has to be scheduled and monitored. Events after the most recent
  checkpoint are not protected from clean tail deletion.
- The audit log remains JSONL and grows without bound; retention and an external
  audit/SIEM store remain production work.

## Alternatives considered

- **Only document `expected_count`** — rejected: it leaves every deployment to
  invent a checkpoint format and makes omission likely.
- **Write the checkpoint next to the log without a key** — rejected: the same
  filesystem writer can alter both files.
- **Claim Git is the anchor** — rejected: it is optional in runtime deployments,
  does not record reads and can itself be rewritten by a privileged actor.
- **Adopt WORM or managed SIEM now** — deferred: appropriate for production, but
  it adds vendor and operations scope before a real pilot proves the workflow.

## References

- [ADR-0015](0015-append-only-tamper-evident-audit-chain.md)
- `saleswiki_mcp/audit.py`
- `scripts/audit_anchor.py`
- `docs/DEPLOYMENT.en.md`
