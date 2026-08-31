---
status: Accepted
date: 2026-08-30
deciders: SalesWiki maintainers
---

# ADR-0025: Bind demo persona switching to an opaque server session

## Context

The Workbench needs to demonstrate how different SalesWiki roles see and act on
the same synthetic knowledge. A browser-side role picker, query parameter, or
client-provided claim would be misleading: it would let the client assert the
very identity that the permission boundary must verify.

## Decision

The demo-only BFF exposes configured fixture personas as labels, but keeps the
role mapping on the server. The browser sends only one allowlisted fixture id to
change an opaque, in-memory, short-lived `HttpOnly; SameSite=Strict` session.
Every MCP invocation is constructed by the BFF using that session's
server-resolved actor. The option is configuration-gated and rejected outside
`profile = "demo"` with `identity_provider = "fixture"`; the BFF still refuses
every non-synthetic vault.

The production replacement remains per-request OIDC identity. In that mode the
server presents the authenticated person and does not expose a persona switch.

## Consequences

- A facilitator can demonstrate sales, marketing, RevOps, curator and admin
  viewpoints without restarting the local BFF.
- A role, access boundary, vault path, MCP tool and credentials never become
  browser request parameters.
- The memory-only fixture session is explicitly a demo convenience, not login,
  authorization for real data, or a substitute for TLS and SSO.
- Deployments with real people must implement the existing OIDC design and
  audit the authenticated immutable subject per request.

## Alternatives considered

- **Client-side role state** — rejected: it makes authorization look like a UI
  setting.
- **Restart the BFF per persona** — safe but too cumbersome for a role demo.
- **Use the fixture selector in production** — rejected: production must use
  signed, validated per-request identity.

## References

- `integrations/workbench/server.py`
- `integrations/workbench/.env.example`
- `docs/engineering/permissioned-knowledge-sso-design.md`
- ADR-0022
