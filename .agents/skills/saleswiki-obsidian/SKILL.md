---
name: saleswiki-obsidian
description: Work on SalesWiki, an Obsidian-first sales and marketing wiki-brain. Use for Markdown entity cards, Obsidian Bases dashboards, Canvas maps, research intake, source tracking, dedupe/corroboration, setup docs, health/index checks and git commits.
compatibility: Designed for Codex or any Agent Skills-compatible agent. Operates on the SalesWiki Obsidian Markdown vault; needs Python 3 for scripts/health_check.py and scripts/build_indexes.py.
metadata:
  author: SalesWiki
  version: "1.0"
---

# SalesWiki Obsidian Skill

Use this skill when changing SalesWiki vault files or answering how the system should be maintained.

## Core Context

Read these files first when relevant:

- `AGENTS.md` - authoritative agent rules for the project.
- `README.md` - project entry point.
- `docs/SETUP.en.md` - setup from scratch.
- `wiki/processes/obsidian-skills.md` - how Obsidian Markdown, Bases, Canvas and web cleanup should be used.
- `wiki/processes/entity-card-governance.md` - Controlled Profile and Live Intelligence rules.
- `wiki/processes/tracking-dedupe-corroboration.md` - source tracking and evidence rules.
- `wiki/processes/access-and-redaction-policy.md` - sensitive data and sharing rules.
- `wiki/processes/data-engineering-contract.md` - stable IDs, ingest runs, derived indexes and synthetic fixture rules.
- `wiki/processes/dashboard-contract.md` - required dashboards and Markdown snapshot rules.
- `wiki/processes/demo-vault.md` - isolated synthetic demo data rules.
- `wiki/processes/external-vault-import.md` - interactive import process for existing vaults.
- `wiki/processes/scoring-configuration.md` - user-approved scoring config change process.
- `wiki/processes/event-research-profile.md` - supervised event research profile, Playwright rules and event pilot output contract.
- `wiki/processes/permission-boundary-blueprint.md` - physical access split before sensitive ingest.
- `wiki/processes/file-drop-ingest-contract.md` - first file-drop ingest contract for raw/imports workflows.

## What To Do

- Treat the repository as an Obsidian vault.
- Prefer Markdown, YAML properties, `[[wikilinks]]`, backlinks and Obsidian graph conventions.
- Keep raw evidence in `raw/` and compiled knowledge in `wiki/`.
- Update `tracking/` whenever a source is checked, accepted, rejected or deduplicated.
- Preserve `Controlled Profile` unless the user explicitly requests a change or review approves it.
- Put mutable research findings in `Live Intelligence`, evidence sections and tracking ledgers.
- Keep `.base` dashboards in `dashboards/` and make them valid YAML.
- Keep generated dashboard snapshots in `reports/dashboard-snapshots/` derived from indexes, not hand-authored as source of truth.
- Keep `.canvas` files JSON-valid if Canvas maps are added.
- Preserve stable `entity_id`, `template_version`, source lineage fields and ingest-run references when updating real cards.
- Keep scoring weights, bands and penalties in `schemas/scoring-models.json`; do not change them without explicit user-approved configurator flow.
- Keep event-research output scope, source priorities, action thresholds and pilot limits in `schemas/event-research-profile.json`.
- Run `python3 scripts/health_check.py` after structural changes.
- Run `python3 scripts/build_indexes.py` after creating, renaming, archiving, merging or materially relinking real entity cards.
- Run `python3 scripts/build_dashboard_snapshots.py` after index rebuilds when dashboard reports should be refreshed.
- Use `python3 scripts/import_external_vault.py` only after user-approved import scope/mapping; it stages packages and plans, not blind production card writes.
- Use `python3 scripts/generate_demo_vault.py --reset` to regenerate isolated synthetic demo data under `demo/`.
- Commit completed changes.

## What Not To Do

- Do not treat codebase-memory tooling as the default discovery layer unless real application code is added.
- Do not rewrite or delete raw evidence.
- Do not bypass access labels, redaction rules or personal-data restrictions.
- Do not silently overwrite non-empty Controlled Profile fields.
- Do not use `.base`, `.canvas` or derived indexes as the only source of truth.
- Do not assume external skills such as `obsidian-markdown`, `obsidian-bases`, `json-canvas`, `defuddle` or `obsidian-cli` are installed.

## Optional External Skills

If the local runtime has `kepano/obsidian-skills` installed:

- Use `obsidian-markdown` for Obsidian Markdown syntax.
- Use `obsidian-bases` for `.base` dashboards.
- Use `json-canvas` for `.canvas` maps.
- Use `defuddle` for web-to-Markdown cleanup during research intake.
- Use `obsidian-cli` only as an optional live-app helper.

These are helpers. SalesWiki process docs remain authoritative.
