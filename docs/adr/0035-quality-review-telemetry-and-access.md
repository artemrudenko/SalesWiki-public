---
status: Proposed
date: 2026-10-01
deciders: SalesWiki maintainers
---

# ADR-0035: Keep data-quality review history separate from access audit

## Status

Proposed

## Context

The current access audit records who accessed or changed resources and under
which authorization decision. A stale card raises a different question: why did
the review happen late, and did the stale information affect a decision? A
single-operator pilot can answer this with a private operational log, but a
multi-user service may need a structured event stream. Existing roles already
cover data quality and review work; a broad new auditor role could expose more
customer context than required.

## Decision

Keep security/access audit and data-quality review history as separate event
purposes. For the private pilot, record the stale-review lifecycle in its own
private log using record handles, timing, source references, outcome, cause
status, decision impact and next action. Do not copy customer content into the
log; use `unknown` when the available history does not establish a cause.

Before implementing a shared event stream or adding an `internal_auditor` role,
evaluate the pilot. If independent review is needed, prefer a read-only
`quality_audit` capability over minimized event metadata. Department leads keep
their existing team scope; RevOps and Curators use their existing role access.
No audit capability grants broader customer-content access or write access.
Corrections continue through proposal, approval and the single-writer worker.

## Consequences

**Positive**
- Separates security investigations from operational data-quality analysis.
- Makes delay, ownership and recurring failure patterns measurable.
- Makes unknown causes explicit and avoids agent-generated explanations.
- Keeps audit access narrower than sales or customer-content access.

**Negative / trade-offs**
- A pilot operator has a small additional logging task.
- A structured multi-user event stream, retention policy and access surface are
  still future work and require privacy review before implementation.
- The role/capability model is a proposal until the pilot validates the need.

## Alternatives considered

- **Put stale-review details into the security audit log** — rejected because
  access history and process diagnosis have different readers, data needs and
  retention questions.
- **Create a broad internal-auditor role now** — rejected as premature before
  multi-user access and independent review needs are established.
- **Infer a cause from the stale timestamp** — rejected because age alone cannot
  distinguish old source data, failed sync, missing ownership or a missed task.

## References

- [Permissioned knowledge architecture](../engineering/permissioned-knowledge-architecture.md#data-quality-review-history-is-a-separate-purpose)
- [Lead-priority pilot runbook](../engineering/permissioned-knowledge-pilot-runbook.md#record-the-review-not-just-the-stale-count)
- `saleswiki_mcp/audit.py` — current tamper-evident access/governance audit
- [Government Data Quality Framework](https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework-guidance)
- [Data Quality Issues Framework](https://www.gov.uk/government/publications/implement-a-data-quality-action-plan/data-quality-issues-framework)
