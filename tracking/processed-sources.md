# Processed Sources

Use this ledger for every reviewed URL, file, article, event page, transcript,
search result or note.

## Fields

| Field | Meaning |
| --- | --- |
| `source_id` | Stable ID, usually date plus normalized domain/title hash. |
| `canonical_url_or_path` | Canonical URL or raw file path. |
| `normalized_title` | Clean title without tracking noise. |
| `source_type` | `news | event-page | company-page | article | post | transcript | crm | note | search-result`. |
| `entities` | Companies, people, events, deals or topics. |
| `first_seen` | First collection date. |
| `last_checked` | Most recent review date. |
| `status` | `accepted | rejected | duplicate | superseded | queued | needs-review`. |
| `duplicate_of` | Source ID or URL if duplicate. |
| `corroborates` | Claim IDs or wiki pages this supports. |
| `output_pages` | Wiki pages created or updated. |
| `notes` | Short decision reason. |

## Ledger

| source_id | canonical_url_or_path | normalized_title | source_type | entities | first_seen | last_checked | status | duplicate_of | corroborates | output_pages | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
