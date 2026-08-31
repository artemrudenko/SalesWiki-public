# Deletion And Archiving

Deleting an entity can break links, tracking records, reports and audit history. Use archiving by default.

## Who Can Delete

Deletion should be restricted to:

- vault admin
- curator
- data/privacy owner for sensitive records
- explicit user-approved agent action

Normal research agents should not delete entity cards.

## Preferred Actions

Use these actions in order:

1. Merge duplicates.
2. Mark as duplicate and link to canonical entity.
3. Archive inactive entity.
4. Redact sensitive fields.
5. Delete only when required.

## Deletion Request Workflow

1. Set `deletion_status: delete-requested`.
2. Add reason in `Review Needed`.
3. Add entry to `state/deletion-requests.md`.
4. Check backlinks and affected indexes.
5. Curator/admin approves or rejects.
6. If approved, archive or delete.
7. Update indexes, graph exports, tracking records and `wiki/log.md`.

## Archive Workflow

When archiving:

- set `deletion_status: archived`
- set `status: archived` when the template has status
- add archive reason
- keep backlinks intact
- move obsolete live intelligence to history if needed
- update index and graph

## Duplicate Merge Workflow

When merging duplicates:

- choose canonical entity
- set duplicate card `deletion_status: duplicate`
- link duplicate to canonical card
- move unique sourced facts to canonical card
- update `tracking/dedupe-register.md`
- update backlinks if needed
- update index and graph

