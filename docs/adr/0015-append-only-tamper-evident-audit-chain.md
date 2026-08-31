---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0015: Append-only, tamper-evident audit hash-chain

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The permissioned-knowledge system must record *who accessed or decided what* —
reads, proposals, approvals, applies — independently of git, which only records
what file content changed. Approval records are identity-bound and reference a
proposal payload hash (`Approval Architecture` in
`docs/engineering/permissioned-knowledge-architecture.md`), so the audit trail
itself has to be trustworthy: a later actor must not be able to silently alter or
delete a past audit event. There is no database; the durable store is plain
files in the repo, and the core stays standard-library only.

A first cut wrote chained records but read the last hash and appended in separate
steps. A 2026-06-24 hardening pass (CHANGELOG `[Unreleased]`) found a race: two
concurrent writers could both read the same `prev`, each chain off it, and
silently break the tamper-evident chain — and even a single locked writer could
leave its line buffered, so the next writer read stale on-disk content and
chained off the wrong `prev`.

## Decision

We persist audit events to an append-only JSONL log where each record carries a
`prev` hash and a `hash = sha256(prev + canonical(content))`, forming a chain in
which altering or removing any past record breaks every later hash
(`saleswiki_mcp/audit.py`, verifiable end-to-end via `verify_chain`). We make the
chained append race-safe: read-last-hash and append happen under one exclusive
`flock`, and the new line is `flush()`-ed and `os.fsync()`-ed to disk *before*
the lock is released, so no concurrent writer can chain off a stale `prev`
(`saleswiki_mcp/jsonl.py` `append_computed`). Reads tolerate a torn trailing line
rather than failing the whole log.

## Consequences

**Positive**
- Tamper-evidence: any edit or deletion of an *interior* record, and any corrupted
  line, is detectable by `verify_chain`. Truncating the *newest* records leaves a
  shorter but self-consistent chain, so tail truncation is only detectable against
  an external anchor — pass `verify_chain(path, expected_count=N)` with a count
  held elsewhere (e.g. a git-committed copy).
- Race-safety: concurrent writers cannot fork the chain; the flush+fsync-before-
  unlock guarantees the next writer sees the committed `prev`.
- No database or external dependency — append-only files, standard library only,
  diffable and git-trackable.

**Negative / trade-offs**
- The single-lock read-modify-append serializes audit writes (acceptable at this
  scale) and `fsync` per append costs an I/O round-trip.
- `flock` is advisory and process-local; it does not protect across hosts/NFS, so
  the deployment must keep one writer reaching a given log.
- Tamper-*evidence*, not tamper-*prevention*: a writer with file access can still
  rewrite the whole chain or truncate its tail. Interior edits/deletions are
  detectable; a clean tail truncation is only caught against an external count/hash
  anchor (`expected_count`), so the deployment must anchor the log (git commit or a
  snapshotted count) for full detection.

## Alternatives considered

- **Plain append log without a hash-chain** — rejected: edits/deletions of past
  records would be undetectable.
- **Separate read-then-append (the original code)** — rejected after the
  hardening review: a concurrent (or buffered-write) race could silently break
  the chain.
- **A database with an audit table** — rejected: violates the no-database,
  standard-library-only, file-as-source-of-truth constraint.
- **Rely on git history for audit** — rejected: git records content changes, not
  who read or decided what, and history can be rewritten.

## References

- `saleswiki_mcp/audit.py` (`AuditSink.record`, `_hash`, `verify_chain`)
- `saleswiki_mcp/jsonl.py` (`append_computed` single-lock + flush/fsync, torn-tail-tolerant reads)
- `CHANGELOG.md` (`[Unreleased]` → "Audit hash-chain race fixed")
- `docs/engineering/permissioned-knowledge-architecture.md` ("Approval Architecture")
