---
status: Accepted
date: 2026-08-31
deciders: SalesWiki maintainers
---

# ADR-0028: Project dashboard signals server-side from dated observations

## Context

The Workbench initially rendered dashboard cards from browser fixtures. That is
useful for visual design but cannot become a production reporting mechanism:
the browser could aggregate a wider account list, and a trend with only one
snapshot would overstate certainty.

## Decision

We expose a narrow `saleswiki.dashboard` read tool returning
`saleswiki.dashboard-view` v1. It reads append-only dated observations and
projects risk, coverage and signals only after the same RBAC+ABAC checks used by
other read tools. A trend requires at least two permitted observations. The
synthetic demo observation ledger is generated with the demo vault and is
explicitly labelled synthetic.

## Consequences

**Positive**
- Dashboard metrics have a policy and provenance boundary.
- A role cannot infer hidden accounts from client-side aggregation.
- The production path can replace only the observation writer, not the UI
  contract.

**Negative / trade-offs**
- Initial data is sparse and must honestly show `insufficient-history`.
- A real pilot needs a reviewed observation writer and storage outside this
  repository.

## Alternatives considered

- **Keep derived dashboard data in React** — rejected because access filtering
  and historical claims would be browser-controlled.
- **Use an LLM to infer trend lines** — rejected because an LLM cannot be a
  system of record or access boundary.

## References

- `saleswiki_mcp/dashboard.py`
- `docs/engineering/self-contained-demo-foundation.md`
- `docs/engineering/workbench-dashboard-v1.md`
- `docs/adr/0022-demo-workbench-bff-over-mcp-stdio.md`
