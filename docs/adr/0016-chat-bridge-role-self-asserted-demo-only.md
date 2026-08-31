---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0016: Rocket.Chat bridge role is self-asserted (demo only); SSO is the production story

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The 0.4.0 milestone (CHANGELOG) shipped a chat-first demo: employees query the
permissioned vault from a Rocket.Chat channel and get role-aware, cited answers
over a synthetic demo vault, with the full governance loop driven from chat
(`integrations/rocketchat/bridge.py`, stdlib-only). The goal of this track is to
show the *access experience* — different roles see different slices, no-leak
hints, the propose→approve→apply loop — to non-technical stakeholders, fast.

Wiring real per-request SSO into a chat bridge would mean an OIDC HTTP flow,
token verification and group→role mapping (ADR-0013,
`docs/engineering/permissioned-knowledge-sso-design.md`). For a demo, that
machinery is disproportionate and gets in the way of switching between roles
live in front of an audience.

## Decision

We let the Rocket.Chat bridge resolve its role from a self-asserted chat command
(`role: account-exec`, RU/EN aliases), mapping the chosen role to a demo actor id
and calling the same role-aware `saleswiki_mcp` core (so retrieval, no-leak and
governance are real even though the identity is not). We scope this explicitly to
the demo track: the bridge logs in as a normal non-admin user, runs against a
throwaway demo vault, and its README, module docstring and CHANGELOG all state
that the role is self-asserted and that production deployments resolve the role
from SSO. SSO/OIDC remains the production identity story; the chat bridge does not
change it.

## Consequences

**Positive**
- Live, frictionless role-switching demonstrates the full access experience in
  one channel without standing up an IdP.
- The bridge exercises the genuine permissioned core (real RBAC/ABAC,
  no-leak, governed write loop), so what the audience sees is accurate behaviour.
- Stdlib-only, throwaway-vault demo touches nothing in the repo and needs no
  secrets.

**Negative / trade-offs**
- Self-asserted role is **not** an access control: anyone in the channel can
  claim any role, so the bridge must never run against real data.
- Two identity paths now exist (demo self-assert vs. production SSO); the
  demo-only boundary must stay clearly documented to avoid misuse.
- The chat demo does not validate the eventual SSO integration itself.

## Alternatives considered

- **Wire real SSO into the bridge** — rejected: pulls forward deferred OIDC work
  and makes live role-switching cumbersome for no demo value.
- **Per-Rocket.Chat-user fixed role mapping** — rejected: still not real auth,
  and it blocks the one-person "switch through every role" demo flow.
- **No chat demo (Claude/MCP client only)** — rejected: loses the
  non-technical, chat-first reach that the 0.4.0 milestone targets.

## References

- `integrations/rocketchat/bridge.py` (`role:` command, `resolve_role`, `ROLES`)
- `integrations/rocketchat/README.md` ("demo track … role is self-asserted")
- `docs/engineering/permissioned-knowledge-sso-design.md` (production SSO path)
- `CHANGELOG.md` (`[0.4.0]` Rocket.Chat demo bridge), `CLAUDE.md`, `AGENTS.md`
- ADR-0013 (MVP fixture identity; SSO deferred)
