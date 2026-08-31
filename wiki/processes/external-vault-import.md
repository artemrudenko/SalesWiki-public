# External Vault Import

Parent intake process: `ingest.md`. External vault import must be human-in-the-loop. Existing team vaults usually mix durable knowledge, meeting notes, drafts, personal data, attachments and obsolete pages. Do not import blindly.

## Import Phases

### 1. Audit

The agent scans the source vault and produces a read-only audit:

- folder tree summary
- Markdown file count
- attachment/raw file count
- detected frontmatter keys
- detected wikilink patterns
- likely entity candidates: companies, people, deals, calls, sources, topics
- possible sensitive data locations
- duplicate or near-duplicate candidates
- unsupported or ambiguous structures

No production files are changed during audit.

### 2. Scope Selection

The agent asks the user what to import:

- all candidate companies
- selected companies/accounts
- people/contact notes
- deals/opportunities
- calls/meetings/transcripts
- sources/news/research
- marketing knowledge
- attachments/raw evidence

The user may exclude folders, tags, date ranges or access classes.

### 3. Mapping

The agent proposes a mapping:

| External structure | SalesWiki target |
| --- | --- |
| folder/path pattern | card type or raw folder |
| frontmatter key | SalesWiki property |
| wikilink pattern | relationship type |
| attachment type | raw folder |
| tag | type/status/access hint |

Questions are asked only when a safe default cannot be inferred.

### 4. Import Plan

Before writing, the agent produces:

- cards to create
- cards to update
- raw files to reference or copy
- duplicates to merge or skip
- access labels
- unresolved questions
- estimated health-check/index impact

### 5. Execute

Only after user approval:

1. Create an `ingest_run_id`.
2. Create/update cards using SalesWiki templates.
3. Preserve external names as aliases where useful.
4. Preserve source paths and add lineage fields.
5. Update tracking ledgers.
6. Run `python3 scripts/health_check.py`.
7. Run `python3 scripts/build_indexes.py`.
8. Run `python3 scripts/build_dashboard_snapshots.py` when imported cards should appear in reports.

## Interactive Agent Behavior

The import assistant should:

- start with a user-provided path
- audit before writing
- show a concise import menu
- ask for mapping/access decisions only when needed
- prefer dry-run plans over immediate writes
- never ingest personal data without explicit boundary/approval
- keep every step reversible until execution is approved

## Minimum Tooling

Implemented scripts:

- `scripts/audit_external_vault.py` - read-only audit and import-plan helper.
- `scripts/import_external_vault.py` - dry-run planner and approved staging executor.

The importer executor is deliberately conservative. It stages an import package under `raw/imports/<ingest_run_id>/` and writes the reviewed plan to `state/import-plans/`; it does not blindly overwrite production entity cards.

Dry run:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault
```

Approved staging after user review:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault --run-id external-vault-YYYYMMDD --execute
```

If the permission boundary is approved and files should be copied into SalesWiki raw storage:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault --run-id external-vault-YYYYMMDD --allow-sensitive --copy-files --execute
```

After staging, the import assistant or curator maps staged notes into typed SalesWiki cards and then runs the normal health/index/snapshot checks.
