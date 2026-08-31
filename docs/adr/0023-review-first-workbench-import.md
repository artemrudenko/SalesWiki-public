---
status: Accepted
date: 2026-08-29
deciders: SalesWiki maintainers
---

# ADR-0023: Review-first Workbench import

## Status

Accepted

## Context

Small teams often begin with a HubSpot CSV export or a note after a meeting. Blindly converting it into cards would create duplicate companies, leak personal data into the vault and bypass the existing proposal → approval → single-writer boundary.

## Decision

The Workbench accepts only a small pasted CSV or structured meeting note. It creates visible, local drafts for the currently open company and requires the user to review them. A mismatch is held for manual matching. Confirmation sends only a bounded, concise summary and the known target entity through the `saleswiki.ingest_resource` proposal tool. The raw text and files do not cross the browser-to-BFF boundary and no entity card is created by this interaction.

## Consequences

**Positive**

- New users can see the value of a structured import without trusting an opaque automation.
- The current proposal, review, audit and worker model stays intact.
- The first browser write route has a deliberately small, testable payload.

**Negative / trade-offs**

- A reviewer still performs the final mapping into typed cards.
- The first release cannot create a previously unseen company automatically.
- Browser paste is suited to small extracts, not bulk migrations.

## Alternatives considered

- **Browser writes Markdown cards directly** — rejected because it bypasses review, authorization and the single writer.
- **Upload full CSVs to the demo BFF** — rejected because raw exports may carry personal data and would expand the BFF's retention/security scope.
- **Build a HubSpot connector first** — deferred until the CSV workflow proves useful in a pilot and vendor-first connector gates are met.

## References

- `prototypes/knowledge-workbench/src/importDrafts.js`
- `integrations/workbench/server.py`
- `wiki/processes/file-drop-ingest-contract.md`
- `docs/engineering/workbench-controlled-import.md`
- [ADR-0011](0011-read-propose-gateway-single-writer-worker.md)
