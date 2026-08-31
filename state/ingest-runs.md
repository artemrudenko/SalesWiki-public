# Ingest Runs

Track every manual, scheduled or automated ingest/research run. A run may
process URLs, raw files, CRM exports, call transcripts, event pages or synthetic
test fixtures.

| ingest_run_id | date | runner | source_scope | input_count | accepted_count | rejected_count | duplicate_count | error_count | output_pages | index_rebuild | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## ID Format

Use `ingest-YYYYMMDD-<short-scope>-<sequence>` for real runs and
`synthetic-YYYYMMDD-<scope>-<sequence>` for test-only fixture runs.

## Rules

- Every accepted or rejected source should also be represented in `tracking/processed-sources.md`.
- Every generated or updated evidence/entity card should store the run ID in `ingest_run_id` when applicable.
- Synthetic fixture runs must use the `synthetic-` prefix and must not be mixed into production `wiki/entities/`.
