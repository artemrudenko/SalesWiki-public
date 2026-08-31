---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0006: Configuration-first: schemas as machine-readable contracts

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

Behavior that changes over time — allowed property values, lead/deal scoring weights and bands, connector scopes, agent routing, event-research limits — was at risk of being hard-coded into scripts, skills and subagent prompts. That spreads the same rule across many files, makes review impossible, and lets agents quietly change business logic (e.g. re-weight scoring) during ordinary work. The project needed a single, reviewable, machine-readable source of truth per concern, with prose docs explaining it and a linter validating it. This was established in the README "Принятые решения" list (configurable scoring/connectors/routing/event profiles; machine-readable enum schema as the validation source) and in `wiki/processes/data-engineering-contract.md` and `wiki/processes/scoring-configuration.md`.

## Decision

We make each governed concern configuration-first: a canonical JSON schema is the source of truth, a Markdown process doc is the human explanation, and `scripts/health_check.py` validates the JSON. `schemas/property-vocabularies.json` is the enum source the linter reads (paired with `wiki/processes/property-vocabularies.md`); `schemas/scoring-models.json` holds scoring weights, bands, penalties and default actions (paired with `wiki/processes/scoring-configuration.md`); `schemas/connector-contracts.json`, `schemas/agent-routing.json` and `schemas/event-research-profile.json` cover connectors, routing and event research. Agents may apply config but must not change it during ordinary work; changes go through the documented approval flow and a change ledger (e.g. `state/scoring-change-requests.md`).

## Consequences

**Positive**
- One reviewable file per concern instead of rules scattered across code and prompts (DRY).
- The health check enforces the contract, so config and validation never silently diverge.
- A clear apply-vs-change boundary stops agents from mutating business logic (scoring, scopes) by accident.

**Negative / trade-offs**
- Each schema has a paired Markdown doc that must be kept in sync, adding maintenance overhead.
- Config changes are deliberately slower: approval flow plus a change-ledger entry.
- JSON-as-config is less expressive than code for complex conditional logic.

## Alternatives considered

- **Hard-code rules in scripts and prompts** — rejected: duplicated, unreviewable, and editable by agents mid-task.
- **A single mega-config for everything** — rejected: couples unrelated concerns and makes review and ownership unclear; one schema per concern keeps blast radius small.
- **Docs-only governance (no JSON, no linter)** — rejected: prose cannot be machine-validated, so drift between intent and behavior would go unnoticed.

## References

- `schemas/property-vocabularies.json` + `wiki/processes/property-vocabularies.md`
- `schemas/scoring-models.json` + [[scoring-configuration]] (`wiki/processes/scoring-configuration.md`)
- `schemas/connector-contracts.json`, `schemas/agent-routing.json`, `schemas/event-research-profile.json`
- `scripts/health_check.py` (check_frontmatter_allowed_values, check_scoring_config, check_connector_contracts, check_agent_routing, check_event_research_profile)
- [[data-engineering-contract]] — `wiki/processes/data-engineering-contract.md`
- `README.md` (## Принятые решения)
