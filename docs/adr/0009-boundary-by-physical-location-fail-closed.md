---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0009: Permission boundary is physical location, not a YAML label; default is fail-closed

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

SalesWiki holds data of mixed sensitivity (broad knowledge, sales-confidential
deals, raw personal-data) in one Markdown vault opened directly in Obsidian. The
architecture review concluded that an `access:` or `boundary:` value in YAML
frontmatter is metadata, not enforcement: any process that reads the file reads
the property too, and a typo, copy-paste or omitted label silently mis-classifies
a card. The permissioned-knowledge MVP therefore had to decide what authoritatively
determines a card's boundary, and what happens to a card that matches no rule.

The boundary-by-location rule was established when the permissioned core shipped
(Slice-era work, boundary registry dated 2026-06-03). A hardening pass on
2026-06-24 (CHANGELOG `[Unreleased]`) closed the remaining gap: the original
fallback for an unmatched path was the world-readable `broad` boundary, so a
mis-filed card would have leaked to every role.

## Decision

We make a card's permission boundary a function of its physical location — its
path prefix under the boundary vault root, looked up in `schemas/boundary-registry.json`
`path_map` — and treat the card's own `boundary:` YAML property as convenience
only. We also make the default fail-closed: a card whose path matches no known
prefix resolves to a `quarantine` boundary that no role lists, so it is blocked
rather than leaked, and `health_check` flags any such mis-filed card for correct
filing. The fallback is hard-coded to `quarantine` in `boundaries.py` so a broken
or empty registry also fails closed.

## Consequences

**Positive**
- A mis-labelled or unlabelled card cannot be over-exposed: location decides access.
- An unclassified/mis-filed card is invisible to every role and surfaced by the
  health check, so it is fixed, never quietly served.
- Storage permissions (OS ACLs, separate folders) can be layered on the same
  physical split, since location is already authoritative.

**Negative / trade-offs**
- Cards must be filed into the correct folder; moving a card changes its access,
  which is powerful but demands discipline and a health-check gate.
- The integrity check (`check_permissioned_data_integrity`) must confirm the
  `boundary:` property matches the folder, adding a coherence rule to maintain.

## Alternatives considered

- **Trust the `access:`/`boundary:` YAML label** — rejected: a label enforces
  nothing; one typo or omission silently leaks. Listed under "False Security" in
  the architecture doc.
- **World-readable `broad` default for unmatched paths** — the original behavior;
  rejected in the 2026-06-24 hardening pass because a mis-filed card would default
  to readable-by-everyone, the opposite of fail-safe.
- **Separate git repo per boundary** — deferred (see ADR in the deployment doc):
  more isolation but heavier ops; revisit only if employees need direct vault access.

## References

- `saleswiki_mcp/boundaries.py` (`resolve_boundary`, `quarantine` fallback)
- `schemas/boundary-registry.json` (`path_map`, `default_boundary: quarantine`)
- `scripts/health_check.py` (`check_permissioned_data_integrity`)
- `CHANGELOG.md` ([Unreleased] → "Fail-closed default boundary")
- [[permissioned-knowledge-architecture]] (Data Boundaries, Reality Check)
