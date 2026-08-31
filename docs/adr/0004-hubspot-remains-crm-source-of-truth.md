---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0004: HubSpot remains the CRM source of truth; SalesWiki proposes, never overwrites

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The sales team operates in HubSpot: owners, lifecycle stages, deal stages, contact fields and activity all live there and drive day-to-day work. SalesWiki adds research, scoring, call analysis and enrichment context on top, and HubSpot enrichment/writeback is a near-term focus. The risk is that an automated agent silently overwrites curated CRM data or pushes low-confidence values into the system the sales team trusts.

The forces: enrich and explain CRM data without becoming a competing system of record, keep every writeback auditable and approvable, and never store HubSpot/Webwright API keys in the repository. This was established in `AGENTS.md` and `README.md` ("HubSpot остается CRM source of truth; SalesWiki enriches/proposes, но не перезаписывает без правил") and specified in [[hubspot-enrichment]], [[hubspot-field-matrix]] and the proposal queue `state/hubspot-writeback-proposals.md`.

## Decision

We keep HubSpot as the operational CRM source of truth. SalesWiki enriches and explains CRM data; it does not silently overwrite it. Every HubSpot card fill, field update or task creation is a staged proposal recorded in `state/hubspot-writeback-proposals.md` with `hubspot_id`, previous/proposed value, source, confidence, a field-matrix `mode` (`propose-only` / `approved-writeback` / `system-writeback`) and an approver. No proposal executes automatically. Owner, lifecycle stage, deal stage, email, phone, company domain, personal data and manually curated notes are never auto-overwritten — conflicts go into the enrichment record. API keys and backend keys are stored outside the repository.

## Consequences

**Positive**
- The sales team's CRM stays authoritative and trustworthy; no surprise overwrites of curated fields.
- Every writeback is traceable to a source, confidence and approver via the proposal queue.
- Enrichment still delivers value (AI summaries/scores, risk summaries) through an explicit, reviewable path.
- No credentials in the repo, reducing leak risk.

**Negative / trade-offs**
- Writeback is slower: most changes require human approval before they reach HubSpot.
- Two places hold related data (HubSpot fields and SalesWiki cards/enrichment records), so they can drift between syncs.
- Running real writeback needs external keys and a connector, which is extra setup outside this vault.

## Alternatives considered

- **SalesWiki as system of record with automatic two-way sync to HubSpot** — rejected: would let agents overwrite curated CRM data, break the sales team's trust in HubSpot, and remove the human approval checkpoint.
- **Read-only — never write to HubSpot at all** — rejected: enrichment (AI summaries/scores, risk summaries) is an explicit near-term goal, so a governed propose-then-approve path is preferred over no writeback.

## References

- `AGENTS.md` — HubSpot read/propose/writeback boundaries; key storage rules
- `README.md` — "## Принятые решения" (HubSpot bullet)
- `state/hubspot-writeback-proposals.md` — proposal queue and field meanings
- [[hubspot-enrichment]], [[hubspot-field-matrix]], [[hubspot-lifecycle-mapping]]
- `schemas/connector-contracts.json`, [[connector-contracts]]
