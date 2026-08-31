# Property Vocabularies

Human-readable source of truth for allowed YAML property values across SalesWiki cards. Templates and dashboards must use only these values. Machine validation reads the same enum set from `schemas/property-vocabularies.json`; keep this document and that schema in sync. When a value is marked **proposed**, it is a v1 default that should be confirmed after real usage; **documented** means the value set already appears in the entity template body.

See also: [Global Property Dictionary](global-property-dictionary.md) for which property applies to which card, and [Freshness And Decay](freshness-and-decay.md) for staleness/decay/SLA thresholds.

## Global enums

| Property | Allowed values |
| --- | --- |
| `freshness` | `fresh` \| `stale` \| `needs-research` \| `needs-action` \| `needs-crm-sync` |
| `confidence` / `score_confidence` | `high` \| `medium` \| `low` |
| `access` | `public` \| `internal` \| `sales-confidential` \| `personal-data` \| `legal-review` |
| `profile_lock` | `unlocked` \| `review-required` \| `locked` |
| `deletion_status` | `active` \| `duplicate` \| `archived` \| `delete-requested` \| `deleted-log-only` |
| `monitoring_status` | `active` \| `paused` \| `watchlist` \| `not-monitored` |
| `monitoring_cadence` | `daily` \| `weekly` \| `monthly` \| `trigger-based` \| `event-week` \| `paused` |
| `processed_status` | `queued` \| `accepted` \| `rejected` \| `duplicate` \| `superseded` \| `needs-review` |
| `score_band` | `hot` \| `warm` \| `nurture` \| `low` |
| `evidence_strength` (used on claim cards) | `single-source` \| `repeated-source` \| `multi-source` \| `primary-confirmed` \| `conflicting` |
| `source_access_type` | `free` \| `paid` \| `restricted` \| `licensed` \| `internal-system` |

## Date properties

`created`, `updated`, `last_reviewed`, `last_checked`, `next_check`, `scored_at`, `next_review`, `date_published`, `date_collected`, `crm_last_synced` — all use `YYYY-MM-DD`.

## `status` by card type

`status` is type-specific. The deal and lead lifecycle is **not** carried in `status` — deals use `stage` / `crm_stage`, leads use `pipeline_segment` + `score`. Evidence and reference cards (`news`, `article`, `source`, `person`, `event-participation`) carry no generic `status` either; `health_check` only validates `status` for the types listed below (those present in `card_status_allowed`).

| Type | Allowed `status` values | Source |
| --- | --- | --- |
| company | `target` \| `prospect` \| `customer` \| `partner` \| `competitor` \| `watchlist` | documented |
| event | `watchlist` \| `researching` \| `active` \| `completed` \| `archived` | documented |
| campaign | `planned` \| `active` \| `completed` \| `paused` | documented |
| icp | `draft` \| `active` \| `deprecated` | documented |
| account-plan | `active` \| `on-hold` \| `archived` | proposed |
| product | `active` \| `beta` \| `retired` | proposed |
| customer-success | `onboarding` \| `healthy` \| `at-risk` \| `renewed` \| `churned` | proposed |
| call | (no `status`; use transcript status below) | n/a |
| report | `draft` \| `published` \| `archived` | proposed |
| asset | `draft` \| `active` \| `retired` | proposed |
| buyer-persona | `active` \| `deprecated` | proposed |
| pain-point | `active` \| `archived` | proposed |
| objection | `active` \| `resolved` \| `archived` | proposed |
| use-case | `active` \| `archived` | proposed |
| competitor-intel | `active` \| `archived` | proposed |
| case-study | `draft` \| `review` \| `published` \| `retired` | proposed |
| private-case | `draft` \| `sanitized` \| `internal` \| `public` | proposed (mirrors promotion pipeline) |
| topic | `active` \| `archived` | proposed |
| channel | `active` \| `paused` \| `retired` | proposed |
| content-brief | `draft` \| `approved` \| `in-production` \| `published` | proposed |
| content-calendar-item | `planned` \| `scheduled` \| `published` \| `cancelled` | proposed |
| outreach-sequence | `draft` \| `active` \| `paused` \| `retired` | proposed |
| experiment | `planned` \| `running` \| `completed` \| `abandoned` | proposed |
| scoring-model | `draft` \| `active` \| `deprecated` | proposed |
| enrichment-record | `queued` \| `enriched` \| `proposed` \| `applied` \| `rejected` | proposed |
| claim | `active` \| `retracted` \| `superseded` | proposed |
| task | `open` \| `in-progress` \| `blocked` \| `done` \| `no-action` | proposed |

## Other type-specific enums

| Property | Card | Allowed values | Source |
| --- | --- | --- | --- |
| transcript status | call | `available` \| `recording-only` \| `needs-transcript` \| `manual-notes` \| `not-available` | documented |
| `pipeline_segment` | lead/deal | `outside-pipeline` \| `qualification-mql` \| `sql` \| `active-deal` \| `disqualified` | documented (lead-monitoring) |
| `lead_type` | lead | `cold` \| `warm` | documented |
| outcome label | scoring feedback | `converted-to-sql` \| `meeting-booked` \| `opportunity-created` \| `closed-won` \| `closed-lost` \| `no-response` \| `bad-fit` \| `stale` \| `nurture-continues` | documented (score-calibration) |
| `reliability` | source | `high` \| `medium` \| `low` | proposed |

## Maintenance

When you add a new card type or change a `status` set, update this table, the entity template body, and run `python3 scripts/health_check.py`. The health check verifies that every property referenced by a dashboard exists in at least one template.
