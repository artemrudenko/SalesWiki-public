---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0013: MVP identity via a fixture provider; SSO/OIDC deferred to a later phase

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The permissioned-knowledge gateway must resolve *who is asking* before any
role-aware retrieval runs, and the role must be resolved server-side so a client
can never choose its own access. The intended production identity source is
Google Workspace / Cloud Identity over OIDC, with Google groups mapped to
SalesWiki roles (`schemas/identity-provider.json` `google-oidc` block, "MVP SSO
Decision" in `docs/engineering/permissioned-knowledge-architecture.md`).

Standing up real OIDC, however, requires an HTTP transport carrying a verified
per-request token, an OIDC adapter, a real tenant, and secret handling — none of
which is needed to prove the core value (role-shaped access, no-leak retrieval,
the governed write loop). The first slices ship as a stdio gateway run by a
single trusted operator, where one process binds one identity. We needed an
identity layer that is correct in shape but cheap to run now.

## Decision

We ship the MVP with a `FixtureIdentityProvider` that resolves a demo `Actor`
(id, role, team, email, owns) server-side from a session/env key
(`SALESWIKI_DEMO_ACTOR`) against the `fixture` provider in
`schemas/identity-provider.json`, and we defer Google OIDC/SSO to a later phase.
Crucially, the core is built identity-agnostic: `IdentityProvider` is a
`Protocol` with a single `resolve() -> Actor`, and every service method already
takes `actor` as its first argument, so OIDC slots in as a second provider plus
a transport switch — not a rewrite. A forward-compatible `google-oidc` block
(`active: false`, group→role map, no committed secrets) reserves the production
path.

## Consequences

**Positive**
- Full role-aware access and no-leak behaviour are demonstrable today without an
  identity vendor, HTTP, or secrets.
- The migration is a server-layer change: add an OIDC provider and resolve the
  actor per request; the policy core is untouched.
- Role is always resolved server-side, never client-chosen, even in the fixture.

**Negative / trade-offs**
- A fixture gateway serves one identity per process; demoing N roles means N
  server entries with different env. It cannot serve many shared users.
- Real authentication, MFA and group-sync are absent until the OIDC phase.
- The fixture roster must be kept aligned with the policy/ABAC roster
  (`org.actors`/`org.teams`), or access can mis-route.

## Alternatives considered

- **Build OIDC/SSO up front** — rejected: large surface (HTTP transport, token
  verification, tenant, secrets) for no extra core value at MVP stage; would
  delay proving the access model.
- **Client-supplied role/header** — rejected: lets the client choose its own
  access, defeating the entire permission boundary.
- **Self-hosted IdP (Keycloak/authentik) for the MVP** — rejected as overkill
  for a single operator; retained only as a fallback if Google is unavailable.

## References

- `saleswiki_mcp/identity.py` (`FixtureIdentityProvider`, `IdentityProvider`, `Actor`)
- `schemas/identity-provider.json` (`fixture` + `google-oidc` blocks)
- `docs/engineering/permissioned-knowledge-architecture.md` ("MVP SSO Decision")
- `docs/engineering/permissioned-knowledge-sso-design.md` (per-request identity)
- [[ROADMAP.en]]
