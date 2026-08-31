---
status: Accepted
date: 2026-08-30
deciders: SalesWiki maintainers
---

# ADR-0024: Governed Workbench review actions through the BFF

## Status

Accepted

## Context

The Workbench already lets a user turn a small note or CSV row into a bounded
proposal. A curator needs a simple way to inspect that queue and record an
approval or rejection without turning the browser into a direct card editor or
letting it choose an actor, role, vault or MCP tool.

## Decision

We expose a narrowly allowlisted review queue and two proposal decisions through
the demo BFF. The server resolves the fixed synthetic actor, calls only
`review_queue`, `approve_proposal` or `reject_proposal`, and validates both
request and response. The browser sends only a proposal identifier, the explicit
action and, for a rejection, a short reason.

The queue includes a server-derived `can_decide` flag. The UI uses that flag to
show or hide decision controls; it never infers permissions from a label or
chooses a role. An approval remains a proposal-state transition: the separate
single-writer worker applies an approved proposal later.

## Consequences

**Positive**

- Curators have a readable proposal inbox linked to the affected account.
- The browser retains no raw imported source and gains no card-write endpoint.
- Role enforcement, append-only decisions and the worker boundary stay in the
  existing MCP governance core.

**Negative / trade-offs**

- The local BFF is still synthetic-demo-only and uses one fixed fixture actor.
- Review summaries are concise metadata, not a substitute for opening the
  governed original evidence in the appropriate workflow.
- Rejections require a short clarification; editing the underlying proposal is
  intentionally a later capability.

## Alternatives considered

- **Approve cards directly from the browser** — rejected: it bypasses the
  proposal, authorization, validation and single-writer boundary.
- **Let the UI select a reviewer role** — rejected: role selection is not
  authentication and would weaken the server-owned identity model.
- **Create a new review database** — rejected: the append-only proposal ledger
  is already the durable review record.

## References

- [ADR-0011](0011-read-propose-gateway-single-writer-worker.md)
- [ADR-0013](0013-mvp-fixture-identity-sso-later.md)
- [ADR-0022](0022-demo-workbench-bff-over-mcp-stdio.md)
- [ADR-0023](0023-review-first-workbench-import.md)
- [`docs/engineering/workbench-review-inbox.md`](../engineering/workbench-review-inbox.md)
