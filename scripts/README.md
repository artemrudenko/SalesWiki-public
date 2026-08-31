# Scripts

Maintenance scripts for SalesWiki.

## First Run

For a fresh clone, run the public demo setup and smoke test:

```bash
python3 scripts/first_run.py
```

Docker equivalent:

```bash
docker compose run --rm first-run
```

The first-run assistant creates `.venv`, installs `requirements.txt`, runs the
public-release review, validates the vault and runs the permissioned demo smoke
test. Add `--full-tests` to also run the full unittest suite.

## Refresh (One Command)

Run the health check, rebuild indexes and rebuild dashboard snapshots in one step:

```bash
python3 scripts/refresh.py            # production contour
python3 scripts/refresh.py --demo     # demo contour
python3 scripts/refresh.py --dry-run  # print the planned steps only
```

The refresh stops at the first failing step and exits non-zero.

## Health Check

Run:

```bash
python3 scripts/health_check.py
```

The check validates:

- required process/state/tracking files
- required raw source directories
- entity template frontmatter
- enum values, stable IDs, template versions, dates and score ranges
- required entity sections
- duplicate entity `type` values
- missing references from `wiki/index.md`
- scoring config integrity: model weights sum to 100, score bands cover 0-100, caps are valid
- connector contract integrity: scopes, write modes, approvals, process docs and audit logs
- connector credential/writeback guardrails: Webwright credential policy and HubSpot proposal queue references
- event research profile integrity: source priorities, required outputs, action rules and pilot limits
- agent routing integrity: referenced skills/agents exist and route handoffs are valid
- agent write-tool guardrails
- demo boundary integrity: demo cards stay under `demo/` and production cards are not synthetic/demo data
- pilot boundary integrity: no `pilot/` directory and no `dataset: pilot` files inside this repository (see `wiki/processes/pilot-data-contract.md`)

## Scoring Config

Canonical scoring config:

```bash
schemas/scoring-models.json
```

Health check validates the config. Agents may apply scoring from this file, but changes to weights, bands, penalties or default actions must go through `wiki/processes/scoring-configuration.md` and be logged in `state/scoring-change-requests.md`.

## Build Indexes

Run:

```bash
python3 scripts/build_indexes.py
```

The index builder reads real cards under `wiki/entities/` and skips `_template.md`. Production builds fail if a real card is missing `entity_id`; `--allow-generated-ids` is reserved for fixtures or migrations. It writes rebuildable artifacts:

- `indexes/entities/entity-registry.csv`
- `indexes/entities/entities.jsonl`
- `indexes/fulltext/documents.jsonl`
- `indexes/freshness/freshness.jsonl`
- `indexes/graph/edges.jsonl` with deduplicated baseline wikilink edges and typed semantic edges from frontmatter
- `indexes/temporal/events.jsonl`

To test with synthetic fixtures without changing production state:

```bash
python3 scripts/build_indexes.py --source-root tests/fixtures/synthetic-vault --output-root /tmp/saleswiki-fixture-indexes --no-update-state
```

Validate fixture counts:

```bash
python3 scripts/build_indexes.py --source-root tests/fixtures/synthetic-vault --output-root /tmp/saleswiki-fixture-indexes --no-update-state --expect-counts tests/fixtures/expected-index-counts.json
```

## Build Dashboard Snapshots

Run:

```bash
python3 scripts/build_dashboard_snapshots.py
```

The snapshot builder reads `indexes/entities/entities.jsonl` and `indexes/freshness/freshness.jsonl`, then writes Markdown reports under `reports/dashboard-snapshots/`:

- `index.md`
- `sales-today.md`
- `deal-risk.md`
- `monitoring.md`
- `marketing-insights.md`
- `data-quality.md`

Use explicit roots for demo or fixture data:

```bash
python3 scripts/build_dashboard_snapshots.py --index-root /tmp/saleswiki-fixture-indexes --output-root /tmp/saleswiki-fixture-reports
```

## Audit External Vault

Run:

```bash
python3 scripts/audit_external_vault.py --source /path/to/external-vault --output /tmp/saleswiki-import-audit.md --json-output /tmp/saleswiki-import-audit.json
```

The audit is read-only. It counts folders, Markdown files, attachments, frontmatter keys, wikilinks, likely entity types and sensitive-data signals so a human can choose import scope before any production write.

## Import External Vault

Dry run:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault
```

Approved staging:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault --run-id external-vault-YYYYMMDD --execute
```

This creates a reviewed plan under `state/import-plans/` and a staging package under `raw/imports/<run-id>/`. It does not blindly write production entity cards.

## Generate Demo Vault

Regenerate the isolated synthetic demo vault:

```bash
python3 scripts/generate_demo_vault.py --reset
python3 scripts/build_indexes.py --source-root demo/demo-vault --output-root demo/indexes --no-update-state
python3 scripts/build_dashboard_snapshots.py --index-root demo/indexes --output-root demo/reports/dashboard-snapshots
```

The generated data lives under `demo/`, is marked `dataset: demo` / `synthetic: true`, and can be deleted or regenerated without approval.

## Generate Demo Digests

Render the "morning digest" demo artifacts (Slack/email-style Markdown produced by the same Answer Contract as the MCP gateway) for three personas:

```bash
python3 scripts/generate_demo_digests.py
```

Output goes to `demo/reports/digests/`. The as-of timestamp is fixed to the demo dataset, so regenerated files only change when the demo data changes.
