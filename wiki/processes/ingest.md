# Ingest Process

Use this process when adding files, URLs, CRM exports, transcripts or research notes.

## Intake

1. Put the source in the correct `raw/` folder.
2. Record source metadata: title, date, origin, owner, access label.
3. Decide entity type: company, person, lead, deal, call, news, source, research.
4. Check whether a wiki page already exists.

## Compile

1. Extract facts, dates, names, claims, decisions and signals.
2. Separate facts from interpretation.
3. Add confidence labels where evidence is weak.
4. Update the smallest relevant wiki pages.
5. Put stable identity/core metadata in `Controlled Profile`.
6. Put research updates, signals and recommended actions in `Live Intelligence`.
7. Link related pages with `[[Wiki Link]]`.

## Validate

1. Every important claim has a source.
2. Freshness fields are updated.
3. Sensitive data has the right access label.
4. Controlled profile fields were not overwritten without explicit approval.
5. `wiki/index.md`, `state/index-status.md` and `wiki/log.md` are updated when needed.

## Output

Every ingest should produce:

- updated wiki page(s)
- one log entry
- updated index entry if a page was created
- follow-up tasks if information is missing

## Specific Ingest Contracts

This is the parent intake process; use the specific contract for the source type:

- `file-drop-ingest-contract.md` - files placed under `raw/imports/`.
- `kb-cleanup-and-drive-ingest.md` - Google Drive KB cleanup and ingest.
- `external-vault-import.md` - importing an existing team vault.
