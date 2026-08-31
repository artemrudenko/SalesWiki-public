---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0001: Obsidian-first Markdown vault as the source of truth

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

SalesWiki needs a durable, queryable knowledge base for sales and marketing — companies, people, leads, deals, calls, events, campaigns and reusable knowledge — that non-technical employees can read and that agents can update reliably.

The constraint set was: keep the knowledge human-readable and diffable, avoid operational dependencies (no required database or server), keep everything version-controlled in git, and let relationships surface as a graph without bespoke tooling. This was established as the first "Принятые решения" bullet in `README.md` ("Obsidian-first: Markdown vault, YAML properties, `[[wikilinks]]`, backlinks, graph view") and is the framing premise of `AGENTS.md` ("Source of truth", "Obsidian conventions", "Obsidian-first discovery") and `CLAUDE.md`.

## Decision

We make an Obsidian-compatible Markdown vault the durable source of truth: raw evidence in `raw/`, compiled knowledge cards in `wiki/`, derived indexes in `indexes/`, operational state in `state/` and `tracking/`. Structured fields live in YAML frontmatter, relationships use `[[wikilinks]]`, and the whole repository opens directly as an Obsidian vault. Indexes under `indexes/` and `.base` dashboards are derived acceleration layers rebuilt from Markdown, never the primary record.

## Consequences

**Positive**
- No required database or server; the vault, health check and indexes run on the Python standard library.
- Knowledge is human-readable, diffable and version-controlled in git, so changes are auditable.
- Obsidian builds the graph, backlinks and properties for free from Markdown links.
- Portable across agent runtimes (Codex, Claude Code, Cursor) because the rules live in `AGENTS.md` / `CLAUDE.md`, not in tool config.

**Negative / trade-offs**
- No enforced schema or referential integrity at write time; consistency relies on `scripts/health_check.py` and discipline.
- `access` labels are metadata, not enforcement — sensitive data needs separate physical/permission boundaries (see [[access-and-redaction-policy]]).
- Large-scale structured querying needs derived indexes, which can drift if not rebuilt after card changes.

## Alternatives considered

- **Conventional relational database / CRM-only system of record** — rejected: introduces an operational dependency, makes content non-diffable and not directly human-readable, and is harder to hand to a non-technical employee or another agent runtime.
- **Plain unstructured documents (e.g. a wiki/docs tool with no properties or links)** — rejected: loses the typed properties, `[[wikilinks]]` graph and machine-validatable structure that let agents update cards reliably.

## References

- `README.md` — "## Принятые решения" (Obsidian-first bullet)
- `AGENTS.md` — "Source of truth", "Obsidian conventions", "Obsidian-first discovery"
- `CLAUDE.md` — project overview
- [[card-taxonomy]], [[entity-card-governance]]
- `docs/SETUP.en.md` — "What Is Not A Dependency"
