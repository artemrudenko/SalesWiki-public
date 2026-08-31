# Access And Redaction Review Queue

Use this queue for access-label changes, sanitized-summary approvals, personal-data export approvals, legal review, and suspected sensitive-data exposure.

| request_id | date | requester | item | current_access | requested_access | reason | reviewer | status | decision | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |  |

## Status Values

- `queued`
- `approved`
- `rejected`
- `needs-redaction`
- `legal-review`
- `done`

## Immediate Rules

- Do not lower access from `sales-confidential`, `personal-data` or `legal-review` without reviewer approval.
- Do not export or share `personal-data` unless the request is approved here.
- Put uncertain customer claims, sensitive private cases and transcript excerpts into `legal-review` or `needs-redaction`.
