---
status: Accepted
date: 2026-08-29
deciders: SalesWiki maintainers
---

# ADR-0021: Use a layout-neutral MCP graph read model

## Status

Accepted

## Context

The accepted Knowledge Workbench design shows a focused company graph with
people, deals, calls, competitors and evidence. The current `company_brief`
Answer Contract is designed for readable answers, not for reconstructing stable
nodes and relationships. Parsing its prose in the browser would couple the UI to
wording, weaken citation lineage and invite client-side authorization mistakes.

The same UI must work for any company without generated screenshots or
account-specific layout code. SalesWiki must also preserve authorization before
retrieval, stable IDs, honest missing states, mandatory citations and the
read/propose/single-writer boundary.

## Decision

We introduce a versioned, layout-neutral `GraphView` read model for exploration
clients and expose it through the implemented `saleswiki.entity_graph` MCP tool.

The permissioned core projects only authorized cards and relationships into the
contract. The client validates the response, maps typed entities to reusable
components and calculates positions locally. The contract never contains pixel
coordinates. Graph reads remain separate from proposal tools and the writer.

Official vendor MCP/API data enters the durable graph only through the existing
staged ingest or governed proposal path; the Workbench does not join multiple
provider MCP responses directly.

## Consequences

**Positive**

- one UI and one adapter can render every company;
- policy and citation rules remain in the permissioned core;
- server meaning is independent of React Flow and visual layout;
- stable IDs and typed edges make the contract testable;
- vendor integrations do not become browser-side policy bypasses.

**Negative / trade-offs**

- SalesWiki owns a second versioned read model beside Answer Contract;
- client and server require compatibility and dangling-reference tests;
- one-hop and response limits intentionally omit some relationships;
- remote use still depends on production OAuth identity and MCP hosting;
- a deterministic layout will not be as art-directed as a unique mock per company.

## Alternatives considered

- **Parse `company_brief` Markdown in the browser** — rejected because prose is
  not a stable protocol and exact evidence/edge lineage would be lost.
- **Return React Flow nodes with server-generated coordinates** — rejected
  because it couples the core to one UI library and makes responsive layout a
  backend concern.
- **Let the browser query the vault/indexes directly** — rejected because it
  bypasses the permissioned retrieval boundary.
- **Join HubSpot, Slack and other vendor MCP results in the browser** — rejected
  because identity, dedupe, freshness and citations would fragment across
  providers.
- **Generate a screenshot for each company** — rejected because screenshots are
  not interactive, accessible, searchable or maintainable data products.

## References

- `docs/engineering/mcp-graph-adapter.md`
- `schemas/graph-view.schema.json`
- `prototypes/knowledge-workbench/`
- `saleswiki_mcp/answer.py`
- `saleswiki_mcp/retrieval.py`
- ADR-0011, ADR-0012 and ADR-0020
