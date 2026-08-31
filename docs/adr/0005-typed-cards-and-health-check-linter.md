---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0005: Typed entity cards with required sections, enforced by a health-check linter

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

SalesWiki is an Obsidian-first Markdown vault, not a database, yet agents and scripts must treat it like a small governed data system (`wiki/processes/data-engineering-contract.md`). Free-form notes do not give automations a reliable shape to read, and there is no schema engine to fall back on. The project needed every entity (company, person, lead, deal, call, event, topic, etc.) to share a predictable structure so dashboards, indexes and the permissioned gateway can extract values, and so drift between templates, dashboards and property vocabularies is caught before it ships. This was established in the README "Принятые решения" list (typed cards with required sections; structure validated by a health-check linter) and codified in `AGENTS.md` ("When adding a new card type" requires updating all six touch-points).

## Decision

We type every entity card and give each type a fixed set of required YAML frontmatter keys and required body sections (`Controlled Profile`, `Live Intelligence`, etc.), and we enforce that contract with `scripts/health_check.py` as the project's test: a non-zero exit is a failing build. The linter validates required files, raw dirs, dashboards, template frontmatter and required sections, duplicate `type`, enum values against `schemas/property-vocabularies.json`, real-card IDs/dates/score ranges, dashboard↔template property coherence, freshness coverage, duplicate doc links and dangling wikilinks. Adding a card type requires updating all six touch-points named in `AGENTS.md`.

## Consequences

**Positive**
- Automations, indexes and the gateway can rely on a stable card shape instead of parsing prose.
- Structural drift (missing sections, bad enum values, dangling links, duplicate types) fails fast and visibly.
- Same-type cards stay consistent, so dashboards and snapshots are coherent across the vault.

**Negative / trade-offs**
- Adding or changing a card type is heavier: six coordinated touch-points plus a re-run of the linter.
- Required sections add ceremony to small cards and constrain free-form note-taking.
- The contract lives partly in Python (`health_check.py`) and partly in Markdown, so they must be kept in sync by hand.

## Alternatives considered

- **Free-form Markdown with conventions only** — rejected: no enforcement means silent drift; automations cannot trust card shape.
- **A real database / external schema engine** — rejected: breaks the Obsidian-first, dependency-light model (vault and checks stay standard-library only) and removes git/Obsidian as the source of truth.
- **Validation only at index build time** — rejected: too late and too narrow; the health check must gate templates, dashboards and links, not just instantiated cards.

## References

- `scripts/health_check.py` (check_required_files, check_entity_templates, check_frontmatter_allowed_values, check_real_card_data_quality, check_dangling_wikilinks)
- `AGENTS.md` (Build and test; Testing instructions; "When adding a new card type")
- [[card-taxonomy]] — `wiki/processes/card-taxonomy.md`
- [[data-engineering-contract]] — `wiki/processes/data-engineering-contract.md`
- `README.md` (## Принятые решения)
