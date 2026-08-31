---
status: Accepted
date: 2026-08-29
deciders: SalesWiki maintainers
---

# ADR-0022: Use a demo-only Workbench BFF over MCP stdio

## Status

Accepted

## Context

The Knowledge Workbench needs a real path to `saleswiki.entity_graph`, but a
browser cannot safely start an MCP stdio process or hold server credentials.
The current gateway also binds one fixture actor to one process. That identity
model is valid only for the synthetic demo vault and must not be mistaken for
shared-user authentication.

We want to test the complete UI contract before the hosted Streamable HTTP and
OAuth phase is available. The bridge must preserve the existing policy, audit,
GraphView and vault-guard boundaries without becoming a second application
core.

## Decision

We add a narrow, read-only Workbench backend-for-frontend for local demos. It
accepts only the allowlisted entity-graph request, invokes the official
`saleswiki.entity_graph` tool through the MCP SDK over stdio, and returns only
the validated GraphView `structuredContent`. The actor, vault, runtime path and
tool name are server-owned; the browser cannot provide or override them.

The BFF is configuration-first, loopback-bound by default, no-store, origin
restricted and guarded to synthetic/demo vaults. It is a temporary delivery
adapter, not production identity. A shared or real-data deployment must replace
the fixed fixture actor and stdio child with the hosted Streamable HTTP + OAuth
architecture in the SSO design.

## Consequences

**Positive**

- the browser exercises the real MCP tool and GraphView contract;
- MCP credentials, fixture identity and vault paths never enter JavaScript;
- policy decisions and citations still come from the existing core;
- the UI transport can later switch to hosted MCP without changing graph layout;
- the demo fails closed if it is pointed at a real or unmarked vault.

**Negative / trade-offs**

- one MCP subprocess per request is deliberately simple but inefficient;
- one BFF process represents one fixture actor, not multiple signed-in users;
- CORS/origin checks reduce accidental exposure but are not authentication;
- the local slice has no TLS, SSO, hosted rate limiting or production monitoring;
- the BFF and static prototype are deployed separately; Sites alone cannot host
  the Python adapter.

## Alternatives considered

- **Call the vault or service directly from the browser** — rejected because it
  exposes storage and reimplements the permission boundary client-side.
- **Let the browser choose an actor or role** — rejected because client-asserted
  identity is not authentication and would bypass policy intent.
- **Parse `company_brief` in the BFF** — rejected because GraphView is the stable
  graph protocol and already carries exact evidence links.
- **Build production OAuth immediately** — deferred because it requires a real
  test IdP/tenant, HTTPS resource metadata and broker configuration; the demo
  bridge does not pretend to solve those external prerequisites.
- **Call the Python service in-process** — rejected for this slice because the
  purpose is to verify the actual MCP boundary used by future clients.

## References

- `integrations/workbench/`
- `prototypes/knowledge-workbench/`
- `docs/engineering/mcp-graph-adapter.md`
- `docs/engineering/integration-platform-plan.md`
- `docs/engineering/permissioned-knowledge-sso-design.md`
- ADR-0013, ADR-0019 and ADR-0021
