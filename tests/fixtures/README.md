# Synthetic Test Fixtures

This folder contains fake SalesWiki data for validating scripts and data-quality checks. The contents are not real customer, lead, company or call data.

Rules:

- Every fixture must use `synthetic-` IDs.
- Fixture files must stay outside production `wiki/entities/` and `raw/`.
- Fixtures may be added, regenerated or deleted without additional approval.
- Do not use fixture outputs in real reports, scoring or CRM enrichment.

Run the index builder against fixtures without touching production state:

```bash
python3 scripts/build_indexes.py --source-root tests/fixtures/synthetic-vault --output-root /tmp/saleswiki-fixture-indexes --no-update-state
```

Validate expected output counts:

```bash
python3 scripts/build_indexes.py --source-root tests/fixtures/synthetic-vault --output-root /tmp/saleswiki-fixture-indexes --no-update-state --expect-counts tests/fixtures/expected-index-counts.json
```
