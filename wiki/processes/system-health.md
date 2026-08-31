# System Health

The system needs visible state so employees trust the answers.

## Health Dashboard Fields

- Last ingest time:
- Last research run:
- Last source audit:
- Pages created this week:
- Pages updated this week:
- Stale active companies:
- Hot leads without next action:
- Deals without recent activity:
- Claims needing sources:
- Failed ingest jobs:
- Index rebuild status:

## Quality Checks

`wiki/processes/freshness-and-decay.md` is canonical for these review-staleness windows; change the thresholds there and keep this list in sync.

- No active deal older than 7 days without update.
- No hot lead older than 3 business days without next action.
- No company brief shown as fresh if company news is older than 7 days for active deals.
- No executive tracking page marked fresh if older than 14 days for active target accounts.
- No news item without source URL or raw path.

## Incident Notes

Use `state/incidents.md` for:

- failed imports
- broken sources
- duplicate entities
- wrong summaries
- sensitive data exposure risk

