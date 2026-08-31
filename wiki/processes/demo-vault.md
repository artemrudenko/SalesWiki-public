# Demo Vault

The demo vault is a separate, explicitly synthetic SalesWiki workspace for sales/marketing presentations and hands-on evaluation. It must not pollute production `wiki/entities/`, `raw/`, `tracking/`, `state/` or production indexes.

## Location

Recommended structure:

```text
demo/
  README.md
  demo-vault/
    wiki/entities/
    raw/
    tracking/
    state/
    dashboards/
  indexes/
  reports/
```

The demo vault is opened in Obsidian as `demo/demo-vault`, not as the production project root.

## Data Rules

- Every demo card uses `dataset: demo`.
- Every demo card uses `synthetic: true`.
- Every demo ID starts with `demo-`.
- Demo data may be regenerated or deleted without approval.
- Demo outputs must never be used for CRM, real sales reporting or customer-facing claims.

## Build Commands

Generate or regenerate demo data:

```bash
python3 scripts/generate_demo_vault.py --reset
```

Build demo indexes:

```bash
python3 scripts/build_indexes.py --source-root demo/demo-vault --output-root demo/indexes --no-update-state
```

Build demo dashboard snapshots:

```bash
python3 scripts/build_dashboard_snapshots.py --index-root demo/indexes --output-root demo/reports/dashboard-snapshots --vault-root demo/demo-vault
```

## Presentation Goals

The demo should show:

- Sales Today: who to touch and why.
- Deal Risk: what needs intervention.
- Monitoring: what is due or stale.
- Marketing Insights: topics, pains, objections and content opportunities.
- Data Quality: missing sources, low confidence and access-review items.

## Minimum Demo Dataset

Target minimum:

- 5 companies
- 8-12 leads
- 2 deals
- 2 calls
- 3 source/news items
- 1 sanitized private case
- 1 campaign/content brief
- 5 tasks/reminders

This is larger than `tests/fixtures/`; fixtures validate scripts, while demo data validates user experience.

## Current Demo Dataset

The repository includes a generated demo vault with:

- 5 companies
- 10 leads
- 2 deals
- 2 calls with synthetic raw transcripts
- 3 source cards and raw research notes
- 1 sanitized private case
- 1 campaign and 1 content brief
- 5 tasks/reminders

Regenerate it with `scripts/generate_demo_vault.py --reset` when the demo story changes. Delete `demo/demo-vault`, `demo/indexes` and `demo/reports` when the demo is no longer needed.
