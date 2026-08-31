---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0011: Read/propose-only gateway separated from a single-writer worker

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The permissioned-knowledge MVP lets employees and agents query a vault that holds
sensitive sales, CRM and personal data, and lets them suggest corrections (flag
stale/wrong, request redaction, request access). The risk is that a tool which can
both serve answers to many callers and mutate production cards is a confused-deputy
and concurrency hazard: a buggy or prompt-injected read tool could write, and
parallel writers could corrupt cards or the audit chain. The architecture review
(System/Security architects) called for an SSO → gateway → proposal queue → single
writer runtime. This split was established when the permissioned core shipped and
is canonical in the Component Contract.

## Decision

We split the runtime into two components with a one-way trust boundary. The MCP
gateway (`saleswiki_mcp/server.py`, `service.py`, `governance.py`) is read/propose
only: it serves role-aware answers and writes nothing to production cards — it only
appends draft proposals and audit events to append-only stores, and it never
imports the worker module. A separate single-writer worker (`saleswiki_mcp/worker.py`)
is the only component that mutates production cards: it applies *approved* proposals
while holding an `fcntl.flock` single-writer lock, validating the payload hash and
base-card version, writing atomically (temp + `os.replace`), reverting and
dead-lettering on any post-apply validation failure, with rollback available. The
gateway never invokes apply directly; approval and apply are distinct steps.

## Consequences

**Positive**
- The component callers reach cannot mutate production *cards* directly — a
  compromised or injected read tool has no card-write path; it can only append a
  proposal. (Residual risk, see below: proposals are unsigned, so a compromised
  writer to the shared proposal store can still forge an `approved` record the
  worker will apply. The mitigation is signed approvals.)
- One writer under a lock means no concurrent-write corruption; a crash releases
  the OS lock with no stale-lock deadlock.
- Every change is replayable and reversible: approved proposal → hash/base
  validation → atomic apply → audit event → rollback; failures leave production
  unchanged and go to a dead-letter queue.
- Read, propose and apply can be reasoned about, tested and deployed (read-only vs
  write mount) independently.

**Negative / trade-offs**
- A change is not instant: it must be proposed, approved, then applied by the
  worker, which is slower than direct edit (acceptable and intended for governance).
- Two components plus append-only stores and a worker loop are more moving parts
  than a single editor; worth it for the safety guarantee.
- Single writer is a throughput ceiling — fine at MVP volume; multi-writer was
  explicitly deferred.

## Alternatives considered

- **One tool that reads and writes** — rejected: confused-deputy and concurrency
  risk; no enforced boundary between serving answers and mutating data.
- **Multi-writer / direct concurrent edits** — rejected ("What Not To Build First"):
  needs locking/merge machinery the MVP volume does not justify.
- **Gateway calls the worker in-process** — rejected: that would re-create the
  write path inside the read surface; the gateway never imports the worker by design.

## References

- `saleswiki_mcp/server.py` (read/propose/govern tools; never imports worker)
- `saleswiki_mcp/worker.py` (`apply_approved`, `_single_writer`, `_atomic_write`, `rollback`, DLQ)
- `saleswiki_mcp/governance.py`, `saleswiki_mcp/service.py`
- [[permissioned-knowledge-architecture]] (Component Contract, Approval Architecture)
- `CHANGELOG.md` (Single-writer worker; worker atomicity hardening)
