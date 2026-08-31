---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0010: RBAC + ABAC authorization model

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The permissioned-knowledge MVP serves a 10-15 person go-to-market team with
distinct needs: an SDR should see only the leads/deals assigned to them, an AE
should see their owned accounts plus their team's, while HoS and RevOps see the
whole sales-confidential boundary, and a broad employee viewer sees none of it.
Pure role-based access (RBAC) is too coarse — "all sales sees all sales data" was
explicitly rejected in the architecture doc — but pure attribute-based access
(ABAC) on every card would be heavy to author and reason about for a small team
with no enterprise GRC stack. Personal-data needed a third state between allow
and block: visible only as an opaque handle. The model was established when the
permissioned core shipped and is canonical in `schemas/access-policy.json`.

## Decision

We authorize reads with RBAC plus ABAC, enforced in the gateway before any output
by `PolicyEvaluator` (`saleswiki_mcp/policy.py`). RBAC sets the coarse grant: each
role lists the boundaries it may reach (`schemas/access-policy.json` `roles`).
ABAC then narrows the sales-confidential boundary per role via
`attribute_constraints`: `assigned` (SDR — owner/owned-account only, never the
team's) and `owned_or_team` (AE — owner, team or owned account). The evaluator
returns one of three effects — `allow`, `handle` (personal-data shown only as an
opaque handle) or `block` — and an explicit, approved access grant is an additive
override that can only upgrade a blocked/handle read to allow for that requester,
company and boundary, never widen anything else.

## Consequences

**Positive**
- Same query yields different safe output per role: SDR, AE, HoS and viewer each
  see exactly their need-to-know slice.
- Cheap to operate: roles are config, attribute narrowing is two constraint names,
  no policy server required for the MVP.
- Time-boxed approved grants compose cleanly as upgrades without rebuilding policy.
- The `handle` effect gives personal-data a safe middle state instead of a binary.

**Negative / trade-offs**
- Attribute checks depend on accurate `owner`/`team`/`company` on cards; an
  access-relevant typo could mis-grant, which is why the integrity health check
  validates owner/team against the org roster.
- Only sales-confidential is attribute-narrowed today; finer ABAC (region, purpose)
  is specified in the architecture doc but not yet implemented.

## Alternatives considered

- **RBAC only** — rejected: cannot express "SDR sees only assigned leads"; would
  expose the whole team's pipeline to every salesperson.
- **Full ABAC policy engine (e.g. OPA/Cedar)** — rejected for the MVP: enterprise
  overhead a 10-15 person team doesn't need; the narrow-interface design keeps a
  migration path open if it is ever justified.
- **Binary allow/deny for personal-data** — rejected in favor of the `handle`
  effect so references stay usable without revealing raw bodies.

## References

- `saleswiki_mcp/policy.py` (`PolicyEvaluator`, `Decision`, `_matches_ownership`)
- `schemas/access-policy.json` (`roles`, `attribute_constraints`, `rules`)
- `scripts/health_check.py` (`check_permissioned_data_integrity` — owner/team roster)
- [[permissioned-knowledge-architecture]] (Authorization Model, Role-Aware Products)
