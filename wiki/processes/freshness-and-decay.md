# Freshness And Decay

Canonical thresholds for three **distinct** concepts that were previously scattered across `AGENTS.md`, `hubspot-lifecycle-mapping.md`, `score-calibration.md` and `reminder-and-task-workflow.md`. Those documents should link here rather than restating numbers.

The three concepts are different and must not be conflated:

- **Review-staleness** — when a card's knowledge is considered out of date and needs a fresh check. Drives `freshness` and the monitoring/review queues.
- **Score-decay** — when a lead/deal score loses confidence or a boost expires. Drives `score_confidence` and trigger handling.
- **Reminder/Task SLA** — how fast a follow-up task must be created when an action is missing. Drives the task workflow.

## Canonical table

| Segment / entity | Review-staleness | Score-decay | Reminder / Task SLA |
| --- | --- | --- | --- |
| Company profile | stale after 30 days without review | — | — |
| Company news — active deal | stale after 7 days | — | — |
| Company news — watchlist | stale after 30 days | — | — |
| Executive tracking — active target | stale after 14 days | — | — |
| Hot lead | stale after 3 business days | — | — |
| Lead — outside pipeline | stale after 30 days without review | reduce trigger strength after 30 days no activity | act on manual reminder date only |
| Lead — qualification / MQL | stale after 7 days without review | reduce confidence after 14 days no activity | follow-up/qualification task within 3 business days if next step missing |
| Lead/deal — SQL | stale after 7 days (no next step or no review) | — | — |
| Active deal | stale after 7 days (no update, or past expected next step) | cap deal score at 60 if no next step | deal-next-step task within 2 business days |
| Public trigger (news/event signal) | — | remove trigger boost when older than 60 days | — |

## How `freshness` is set

- `fresh` — within the review-staleness window above.
- `stale` — past the review-staleness window; needs a re-check.
- `needs-research` — key fields are empty or unverified.
- `needs-action` — research is current but an owner action is pending.
- `needs-crm-sync` — wiki and HubSpot disagree or a write-back is pending.

## Agent behaviour

- Apply review-staleness to set `freshness` and to populate the monitoring / review dashboards.
- Apply score-decay only to `score_confidence` and trigger boosts — never silently rewrite the base score weights (see [Score Calibration](score-calibration.md)).
- Apply reminder SLA by creating tasks per [Reminder And Task Workflow](reminder-and-task-workflow.md); record a no-action reason when no task is justified.

## Maintenance

If a threshold changes, change it **here only** and confirm the dependent docs still link back. Keep the three columns separate; a single day-count (e.g. 30 days) can mean different things in different columns.
