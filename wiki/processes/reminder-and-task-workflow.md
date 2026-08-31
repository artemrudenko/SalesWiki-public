# Reminder And Task Workflow

SalesWiki should convert findings into accountable actions. A useful research result ends with a next action, reminder or explicit decision to wait.

Reminder/Task SLA thresholds (e.g. MQL missing next step within 3 business days, deal next step within 2) are canonical in `freshness-and-decay.md`.

## Task Types

- `lead-follow-up`
- `deal-next-step`
- `research-gap`
- `crm-update-review`
- `case-capture`
- `call-follow-up`
- `campaign-handoff`
- `event-outreach`
- `data-quality`

## Task Status

- `open`
- `in-progress`
- `waiting`
- `done`
- `cancelled`
- `overdue`

## Reminder Rules

| Scenario | Reminder behavior |
| --- | --- |
| Outside-pipeline lead without trigger | Set monthly review or trigger-based watch; do not create outreach task. |
| Outside-pipeline lead with credible trigger | Create light-touch follow-up task. |
| MQL/qualification lead missing next step | Create follow-up or qualification task due within 3 business days. |
| Active deal missing next step | Create deal-next-step task due within 2 business days. |
| Call commitment exists | Create task for each commitment with due date/owner. |
| Research gap blocks decision | Create research-gap task. |
| CRM update proposed | Create crm-update-review task for owner/approver. |

## Required Task Fields

Every task should have:

- owner
- due date
- priority
- related entity links
- source/evidence
- expected output
- status
- result

## Overdue Rules

- High priority: overdue after due date passes.
- Medium priority: overdue after 1 business day grace.
- Low priority: overdue after 3 business days grace.

## Agent Behavior

When an agent recommends action:

1. Check whether an open related task already exists.
2. If yes, update it instead of creating a duplicate.
3. If no, create a Task card or queue entry.
4. Link the task from Lead/Deal/Company/Person/Event.
5. Include owner, due date and evidence.
6. Include tasks in HoS and lead monitoring reports.

## No-Action Decisions

Sometimes the right action is no outreach.

Record:

- reason not to act
- next review date
- trigger required
- owner

