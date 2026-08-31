---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0002: Raw evidence is immutable; corrections are appended, never rewritten

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

SalesWiki compiles conclusions from source material: news, articles, call transcripts, CRM exports, event pages and research. For those conclusions to be trustworthy and auditable, the underlying evidence must remain exactly as it was collected — a later "fix" must not silently erase what an earlier source actually said.

This was established in `AGENTS.md` ("Source of truth": *"Do not delete or rewrite raw evidence. If a source was wrong, add a correction note and link both the original and the correction"*) and in the commit guidelines (*"Keep `raw/` evidence immutable; never rewrite source history"*). `README.md` records it as a decision: "Raw-источники не переписываются: исходники живут в `raw/`."

## Decision

We treat everything under `raw/` as immutable source material. Agents save or reference the source in `raw/`, then compile conclusions into `wiki/` cards with citations back to the raw path or URL. When a source turns out to be wrong, we add a correction note and link both the original and the correction rather than editing or deleting the original. Every reviewed source — accepted, rejected or deduplicated — gets a tracking entry under `tracking/`.

## Consequences

**Positive**
- Conclusions stay auditable: any claim can be traced to the exact evidence it was built on.
- Corroboration works — independent sources that say the same thing strengthen confidence (`tracking/corroboration-register.md`) instead of overwriting each other.
- A later agent never re-reviews the same source blindly, because the tracking ledgers record prior decisions.
- Git history of `raw/` is never rewritten, so source provenance is tamper-evident.

**Negative / trade-offs**
- Storage grows monotonically; superseded or wrong sources are kept, not pruned.
- Readers must follow the correction chain to find the current understanding; the raw file alone can be stale or wrong by design.
- Requires discipline and tracking entries even for rejected sources, which is extra process overhead.

## Alternatives considered

- **Edit sources in place to keep only the "current correct" version** — rejected: destroys the audit trail, makes citations unverifiable, and lets a single mistaken edit erase what a source originally said.
- **Delete superseded or wrong sources to save space** — rejected: breaks corroboration and dedupe history and prevents future agents from knowing a source was already reviewed; the project prefers archive/correction over deletion (see [[deletion-and-archiving]]).

## References

- `AGENTS.md` — "Source of truth", "Commit guidelines", "Citation rules", "Required update loop"
- `README.md` — "## Принятые решения" (raw sources / corroboration bullets)
- [[tracking-dedupe-corroboration]], [[source-governance]]
- `tracking/processed-sources.md`, `tracking/corroboration-register.md`, `tracking/dedupe-register.md`
- [[deletion-and-archiving]]
