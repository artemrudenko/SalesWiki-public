---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0003: Separate Controlled Profile from Live Intelligence (profile_lock)

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

Agents process new material against the same entity cards repeatedly during ingest, research and monitoring. Without a boundary, each pass risks rewriting core identity and ownership facts (legal name, website, entity type, owner, access label, canonical links) every time new — and sometimes weaker or conflicting — evidence arrives.

The forces: protect stable identity/core metadata from casual or automated overwrite, while still allowing the high-volume mutable knowledge (signals, news, calls, hypotheses) to be updated freely. This two-layer model was established in `AGENTS.md` ("Entity card governance") and is specified in detail in [[entity-card-governance]] and [[card-taxonomy]]. `README.md` records it as a decision: "`Controlled Profile` отделен от `Live Intelligence`."

## Decision

We split every reusable entity card into two layers and gate the protected one with a `profile_lock` property:

- **Controlled Profile** — stable facts (legal/company name, website, canonical page name, entity type, ownership, access label, core identifiers, canonical relationship links, deletion/monitoring status). Agents may fill missing fields when the source is strong, but must not overwrite a non-empty controlled field unless the user explicitly asks, a trusted sync source provides it, or curator review approves it. Conflicts and proposed controlled-field changes go to `Review Needed`, not into the field.
- **Live Intelligence** — the mutable area updated during normal monitoring, each update carrying a source, confidence and date.

`profile_lock` takes `unlocked` (fill blanks, never overwrite), `review-required` (controlled changes go to `Review Needed`), or `locked` (only explicit user request or curator approval can change controlled profile).

## Consequences

**Positive**
- Core identity records survive routine ingest; agents can run high-frequency monitoring without corrupting canonical facts.
- A clear, machine-checkable place (`Review Needed` + `profile_lock`) for human/curator approval of sensitive changes.
- Cards of the same type share required sections (`card-taxonomy.md`), so employees and agents always know where to look.

**Negative / trade-offs**
- Extra structure and ceremony on every card; contributors must know which layer a fact belongs to.
- Legitimate controlled-field corrections are slower because they route through `Review Needed` and approval.
- `profile_lock` is a convention enforced by agent behavior and `health_check`, not by Obsidian itself — a careless manual edit can still overwrite a locked field.

## Alternatives considered

- **Single flat card with all fields equally editable** — rejected: every monitoring pass could overwrite identity/ownership facts, destroying stability and trust in the canonical record.
- **Per-field permissions or external schema enforcement** — rejected as over-engineered for an Obsidian-first vault; a two-section split plus one `profile_lock` property gives most of the protection while staying human-readable and diffable (consistent with [[ADR-0001|0001]]).

## References

- `AGENTS.md` — "Entity card governance"
- [[entity-card-governance]] — Controlled Profile, Live Intelligence, Profile Lock
- [[card-taxonomy]] — required sections per type
- `README.md` — "## Принятые решения" (Controlled Profile bullet)
- [[access-and-redaction-policy]]
