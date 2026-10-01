---
status: Accepted
date: 2026-09-18
deciders: SalesWiki maintainers
---

# ADR-0034: External GTM methods with a local policy adapter

## Status

Accepted

## Context

SalesWiki's initial licensed-method-library pilot established that method
sources must not become entity facts, policy or scoring (ADR-0033). Reusable
method notes and skills need to serve more than one project, while SalesWiki
must retain its permissioned Answer Contract, citation, freshness and approval
boundaries.

## Decision

We keep generic source manifests, decision lenses, synthetic evaluations and
portable skills in a separate private GTM Methods project. SalesWiki uses a
version-pinned reference and a project-local `saleswiki-method-library` adapter.
The adapter applies method notes only after authorization and deterministic,
cited fact assembly; it can influence presentation shape and evaluation, not
facts or policy.

The initial pin is GTM Methods `v0.1.0`, commit
`a4d5a7adaf07f278ed15f7f7c895b09309a8a420`. It is documentation provenance,
not a runtime dependency.

## Consequences

**Positive**

- Generic GTM practice can be evaluated and reused without copying customer
  material or SalesWiki-specific access rules.
- Skills become promotable to a user-level environment only after evidence of
  cross-project usefulness.
- SalesWiki retains reviewable local method notes and its complete policy
  boundary.

**Negative / trade-offs**

- Method upgrades require an explicit version review and synthetic evaluation.
- Similar method wording may exist in the generic library and the local adapter
  while their purposes differ.
- The initial private project is not a public distribution channel or a runtime
  package manager.

## Alternatives considered

- **Keep every method inside SalesWiki** — rejected because it couples reusable
  practice to one product's facts and policies.
- **Install the first skill globally immediately** — rejected because it has
  not yet demonstrated safe use in two independent consumer projects.
- **Let the generic project feed the Answer Contract directly** — rejected
  because a framework is not authorized customer evidence.

## References

- [[0033-licensed-method-library-is-not-a-fact-store]]
- [[method-library-pilot]]
- [[method-library-intake]]
- [[gtm-methods-integration]]
- `.agents/skills/saleswiki-method-library/SKILL.md`
- `.claude/skills/saleswiki-method-library/SKILL.md`
