---
type: lead
entity_id: synthetic-lead-alpha-buyer
template_version: 1
lead_type: warm
pipeline_segment: qualification-mql
company: "[[Company - Synthetic Alpha]]"
owner: synthetic-owner
source: synthetic-fixture
hubspot_object_type: contact
hubspot_id: synthetic-hs-contact-1
crm_owner: synthetic-owner
crm_stage: MQL
crm_last_synced: 2026-05-29
created: 2026-05-29
updated: 2026-05-29
last_touched: 2026-05-29
next_review: 2026-06-01
score: 72
score_band: warm
score_model: scoring-models-v1/mql
score_confidence: medium
scored_at: 2026-05-29
score_decay:
freshness: needs-action
access: sales-confidential
profile_lock: locked
deletion_status: active
tags:
  - lead
---

# Lead: Synthetic Alpha Buyer

Synthetic fixture lead for validating scoring and action indexes.

## Controlled Profile

- Contact: [[Person - Synthetic Buyer]]
- Company: [[Company - Synthetic Alpha]]

## Live Intelligence

Synthetic lead intelligence.

## Linked Entities

- Company: [[Company - Synthetic Alpha]]
- Person: [[Person - Synthetic Buyer]]
- Deal: [[Deal - Synthetic Alpha - Pilot]]
- Calls: [[Call - Synthetic Alpha - 2026-05-29 - Discovery]]

## Evidence

- Synthetic source only.

## Next Action

- Action: Synthetic follow-up
- Due: 2026-06-01
- Owner: synthetic-owner
- Related task:
- No-action reason:

## Review Needed

- None.

## Change History

| Date | Change | Source/request |
| --- | --- | --- |
| 2026-05-29 | Created synthetic fixture | tests/fixtures |
