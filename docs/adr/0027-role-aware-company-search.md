---
status: Accepted
date: 2026-08-30
deciders: SalesWiki maintainers
---

# ADR-0027: Search companies through a small role-aware resolver

## Context

The first Workbench search field only filtered nodes already present in the
open graph. It looked like product search but could not find another account,
could not represent an honest empty state, and had no server-side access
boundary. A browser-side list of all companies would reveal restricted account
names before the user attempted to open one.

## Decision

Add `saleswiki.company_search(query)` as a deterministic MCP read tool and
expose it through the demo BFF at `GET /api/v1/company-search?q=…`. It accepts
a small query, evaluates each matching company through the existing policy,
and returns at most eight **allowed** records with only an entity ID, label and
freshness metadata. Blocked candidates and their count are omitted.

The Workbench debounces the request and renders its result list in the fixed
top bar. Selecting a result opens the existing role-aware `entity_graph` flow.
This search does not use an LLM and does not search card bodies.

## Consequences

- Users can move from a company name to an authorized graph without changing
  the application shell.
- The server remains the source of truth for discoverability and identity.
- Natural-language questions, body/vector search and LLM intent routing remain
  future additions. Any LLM may choose a tool only after this authorization
  boundary; it never receives the raw vault or substitutes for policy.

## Alternatives considered

- **Filter the loaded graph only** — retained only for graph facets; it is not
  a real search experience.
- **Send a complete account list to the browser** — rejected because it leaks
  restricted names and makes client code responsible for authorization.
- **Start with LLM semantic search** — rejected for the first slice because
  deterministic, cited entity resolution is the safer and more useful base.

