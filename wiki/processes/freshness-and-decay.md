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

## Reviewing a stale signal and finding its cause

A stale signal means that evidence needs checking against the cadence for its
intended use. It does not establish that the fact is wrong, that a sync failed,
or that the account's priority should fall. Keep the review result separate
from the cause of the delay.

Keep source freshness and compiled-card review separate. A source can be verified
after the account summary's last full review; this means the source itself was
checked, not that the summary or recommendation was reconciled with it. Show the
source date and the last full review date separately, then name the next
reconciliation check. The synthetic Atlas Foods example in the Workbench uses
this case: later verified sources are visible, the summary review is overdue,
and the reason it was missed remains unknown.

For a pilot or operational review, record the due, detected, assigned and
resolved times when known; the safe source reference and source date; the
review outcome; whether the decision changed; and the next owner/action. Classify
the cause as confirmed, suspected or unknown. Common categories include an old
source, missed/failed sync, no owner/task, missed task, a wrong review cadence,
conflicting sources or a false alert. Do not infer a cause from age alone; fix
the confirmed recurring cause as close to its source as possible. Keep customer
content out of operational quality logs and keep these logs separate from the
security/access audit.

Useful measures are due-to-detected, detected-to-assigned and
assigned-to-resolved time, unowned reviews, repeat causes and decision-impact
counts. Show record-level next steps to permitted owners; give process-level
trends only to roles already allowed to see them, or later to a narrowly scoped
read-only quality-audit capability if a pilot demonstrates the need.

This loop follows the [Government Data Quality Framework](https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework-guidance)
and its [Data Quality Issues Framework](https://www.gov.uk/government/publications/implement-a-data-quality-action-plan/data-quality-issues-framework):
quality is use-specific, findings are measured over time, and root causes
should be investigated before choosing a fix. These sources inform the method;
they do not prove that SalesWiki currently detects causes automatically.

## Maintenance

If a threshold changes, change it **here only** and confirm the dependent docs still link back. Keep the three columns separate; a single day-count (e.g. 30 days) can mean different things in different columns.
