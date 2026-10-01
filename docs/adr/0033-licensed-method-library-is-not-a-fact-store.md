---
status: Accepted
date: 2026-09-17
deciders: SalesWiki maintainers
---

# ADR-0033: Licensed method library is not a fact store

## Status

Accepted

## Context

SalesWiki needs reusable sales and marketing methods to make repeated tasks
such as call preparation and campaign briefs more complete. A naïve book-RAG
approach would blur general teaching material with live account evidence,
silently import content with incompatible licenses and let an LLM present a
generic framework as a customer fact. That conflicts with the Answer Contract,
the public-preview repository boundary and the prompt-development contract.

## Decision

We keep a small method library with a separate boundary: dated, immutable raw
manifests; source cards with license and exception notes; and compact method
notes that identify one decision, permitted prompt use and limitations.

Method sources may affect presentation checklists and synthetic evaluation.
They never enter deterministic factual answers, alter authorisation or scoring,
or replace current primary evidence. The public repository accepts complete
source copies only after per-asset license review; initial sources remain
canonical remote references.

## Consequences

**Positive**

- Reusable GTM methods become traceable, reviewable and testable.
- Prompt improvements preserve citations, freshness, `missing` and role access.
- License exceptions and commercial-use constraints remain visible.

**Negative / trade-offs**

- This is slower than bulk RAG ingestion.
- The library cannot claim to validate a specific account or market.
- Full-text preservation requires an additional source-asset audit.

## Alternatives considered

- **Put full books into prompts or a general retrieval corpus** — rejected:
  provenance, licensing and fact/method boundaries become unclear.
- **Use only commercial playbooks and free web articles** — rejected for the
  initial public pilot: free access does not imply redistribution or safe reuse.
- **Turn frameworks directly into scoring weights** — rejected: scoring changes
  require the approved scoring-configuration flow and empirical calibration.

## References

- [[method-library-intake]]
- [[method-library-pilot]]
- [[prompt-development-contract]]
- [[0032-role-task-and-user-presentation-profiles]]
- [[0012-answer-contract-extract-only]]
