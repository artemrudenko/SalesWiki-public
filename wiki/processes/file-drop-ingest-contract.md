# File Drop Ingest Contract

Parent intake process: `ingest.md`. This is the first executable ingest contract to implement before external CRM, Drive or Meet connectors. It describes how a file placed under `raw/imports/` becomes tracked evidence and, when appropriate, curated cards.

## Scope

Inputs:

- copied or referenced files under `raw/imports/`
- manually supplied metadata in `state/manual-intake.md`
- synthetic files under `tests/fixtures/` for validation only

Outputs:

- `state/ingest-runs.md` entry
- `tracking/processed-sources.md` entry per reviewed source
- source/evidence card when accepted
- updated entity cards when the source changes current knowledge
- rebuilt derived indexes when real entity cards changed

## Required Run Metadata

Every run needs:

- `ingest_run_id`
- run date
- runner
- source scope
- input count
- accepted/rejected/duplicate/error counts
- output pages

Use `ingest-YYYYMMDD-filedrop-<sequence>` for real runs and `synthetic-YYYYMMDD-filedrop-<sequence>` for fixture-only runs.

## Required Source Metadata

Every accepted source/evidence card should carry:

- `source_id`
- `raw_path`
- `content_hash`
- `ingest_run_id`
- `date_collected`
- `processed_status`
- `access`
- `source_access_type` when the source has licensing/access restrictions

## Idempotency

Before processing a file:

1. Normalize the path.
2. Compute or record a stable `content_hash`.
3. Check `tracking/processed-sources.md` for the same canonical path/hash.
4. If already processed, mark duplicate or no-op instead of creating parallel cards.

## Safety

- Files with possible personal data default to `personal-data` or `sales-confidential`.
- Do not copy transcript excerpts into broad cards.
- If sensitivity is unclear, add a row to `state/access-review.md`.

## Done Criteria

A file-drop run is complete only when:

1. `state/ingest-runs.md` has the run row.
2. Each input has a processed-source ledger row.
3. Accepted outputs have stable IDs and lineage fields.
4. `python3 scripts/health_check.py` passes.
5. `python3 scripts/build_indexes.py` has been run if real entity cards changed.
