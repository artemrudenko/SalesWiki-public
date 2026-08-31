# Data Engineering Contract

SalesWiki is a Markdown-first vault, but agents and scripts must treat it like a small governed data system.

## Layers

| Layer | Path | Role |
| --- | --- | --- |
| Raw evidence | `raw/` | immutable source files and exports |
| Curated cards | `wiki/entities/` | human-readable source of truth |
| Ledgers | `tracking/`, `state/` | processing, dedupe, access and run state |
| Derived indexes | `indexes/` | rebuildable machine-readable outputs |
| Test fixtures | `tests/fixtures/` | synthetic-only validation data |

## Stable IDs

Every real entity card must have:

- `entity_id`
- `template_version`
- `created`
- `updated`
- `deletion_status`

Evidence/source-like cards should also have, when applicable:

- `source_id`
- `raw_path`
- `content_hash`
- `ingest_run_id`

IDs must not depend on the page name. Page names can change; IDs should not be reused after merge, archive or deletion.

## Machine-Readable Schemas

`schemas/property-vocabularies.json` is the machine-readable enum source for `scripts/health_check.py`.

Keep it aligned with:

- `wiki/processes/property-vocabularies.md`
- entity template frontmatter
- dashboard filters and properties

## Ingest Runs

Every import, research sweep, transcript parse or CRM export processing run should create an entry in `state/ingest-runs.md`.

Use:

- `ingest-YYYYMMDD-<scope>-<sequence>` for real runs
- `synthetic-YYYYMMDD-<scope>-<sequence>` for fixture-only runs

## Derived Indexes

Run:

```bash
python3 scripts/build_indexes.py
```

How ids are assigned, kept stable and deduplicated is defined in `identifier-strategy.md` (variant C: an opaque typed ULID core `<type>_<ULID>` minted once via `saleswiki_mcp/ids.py` into an append-only `state/id-ledger.jsonl`, with a readable slug/alias surface and natural-key idempotency). Create production entity cards through the chokepoint `python3 scripts/new_entity.py --type <t> --name "<n>" [--natural-key <k>]` rather than hand-authoring `entity_id`. `health_check` validates the ledger when present.

Production builds fail if a real card is missing `entity_id`. Filename-derived IDs are allowed only when explicitly requested for fixture or migration work:

```bash
python3 scripts/build_indexes.py --allow-generated-ids
```

Generated files:

- `indexes/entities/entity-registry.csv`
- `indexes/entities/entities.jsonl`
- `indexes/fulltext/documents.jsonl`
- `indexes/freshness/freshness.jsonl`
- `indexes/graph/edges.jsonl`
- `indexes/temporal/events.jsonl`

These files are derived. If they are missing or stale, rebuild them from Markdown rather than editing them by hand.

The graph export contains deduplicated baseline `WIKILINKS_TO` edges plus typed semantic edges extracted from selected frontmatter fields such as `company`, `deal`, `participants`, `source_id`, `duplicate_of` and `corroborates`.

## Synthetic Data

Synthetic data lives only under `tests/fixtures/`. It may be added, regenerated or deleted without additional approval.

Rules:

- use `synthetic-` IDs
- never copy synthetic fixtures into production `wiki/entities/`
- never use fixture outputs in real sales, marketing, CRM or reporting workflows
- validate fixture index counts with `tests/fixtures/expected-index-counts.json`
