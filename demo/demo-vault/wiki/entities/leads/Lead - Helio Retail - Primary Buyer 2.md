---
type: lead
entity_id: demo-lead-helio-retail-2
template_version: 1
dataset: demo
synthetic: true
created: 2026-08-29
updated: 2026-08-29
last_reviewed: 2026-08-29
freshness: fresh
confidence: medium
access: sales-confidential
profile_lock: locked
deletion_status: active
tags:
  - lead
  - demo
lead_type: warm
pipeline_segment: outside-pipeline
company: "[[Company - Helio Retail]]"
owner: alex-demo
source: demo-generated
last_touched: 2026-05-29
next_review: 2026-09-05
score: 71
score_band: warm
score_model: scoring-models-v1/mql
score_confidence: medium
scored_at: 2026-08-29
score_decay:
freshness: needs-action
---

# Lead: Helio Retail Primary Buyer 2

## Controlled Profile

- Company: [[Company - Helio Retail]]
- Contact: [[Person - Helio Retail Buyer]]

## Live Intelligence

Synthetic lead with a demo score and explicit next action.

## Score Readout

- Score: 71
- Band: warm
- Top positive factors: ICP fit, recent trigger, stakeholder relevance.
- Top risks: demo data only, no real source.
- Recommended next action: send contextual follow-up and update outcome.
- Owner: alex-demo
- Next review: 2026-09-05

## Linked Entities

- Company: [[Company - Helio Retail]]
- Tasks: [[Task - Follow Up - Helio Retail]]

## Next Action

- Action: Follow up with a short trigger-based note.
- Due: 2026-09-05
- Owner: alex-demo
- Related task: [[Task - Follow Up - Helio Retail]]


## Evidence

- Synthetic demo data only. Do not use for CRM, reporting or customer-facing claims.

## Review Needed

- Delete or regenerate this demo dataset when the presentation is complete.

## Change History

| Date | Change | Source/request |
| --- | --- | --- |
| 2026-08-29 | Created synthetic demo card | demo generator |
