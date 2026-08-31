# Global Property Dictionary

Use these YAML properties consistently across entity cards.

> Authority: allowed property values are canonical in `wiki/processes/property-vocabularies.md` and `schemas/property-vocabularies.json`. Where this dictionary lists allowed values, treat them as a readable mirror of those sources and keep them in sync.

## Core Properties

| Property | Applies to | Meaning | Allowed values / notes |
| --- | --- | --- | --- |
| `type` | all cards | entity type | must match card taxonomy |
| `entity_id` | all cards | stable machine ID independent from page name | opaque `<type>_<ULID>` core minted once via the `scripts/new_entity.py` chokepoint (see `wiki/processes/identifier-strategy.md`); never hand-author or reuse after merge/delete |
| `template_version` | all cards | template/schema version used when creating the card | positive integer |
| `status` | lifecycle cards | current lifecycle state | type-specific |
| `owner` | owned cards | accountable person/team | human or team name |
| `created` | all cards | card creation date | `YYYY-MM-DD` |
| `updated` | all cards | last material card update | `YYYY-MM-DD` |
| `last_reviewed` | durable knowledge | last human/agent review | `YYYY-MM-DD` |
| `freshness` | monitored cards | current freshness state | `fresh`, `stale`, `needs-research`, `needs-action`, `needs-crm-sync` |
| `access` | all cards | data access label | `public`, `internal`, `sales-confidential`, `personal-data`, `legal-review` |
| `profile_lock` | all cards | controlled profile edit policy | `unlocked`, `review-required`, `locked` |
| `deletion_status` | all cards | archive/delete workflow state | `active`, `duplicate`, `archived`, `delete-requested`, `deleted-log-only` |
| `tags` | all cards | broad Obsidian filters | list |
| `aliases` | named entities | alternate names | list |

## Monitoring Properties

Use these on companies, people, events, sources, topics and lead/deal cards when monitored.

| Property | Meaning | Allowed values / notes |
| --- | --- | --- |
| `monitoring_status` | whether monitoring is active | `active`, `paused`, `watchlist`, `not-monitored` |
| `monitoring_cadence` | expected check cadence | `daily`, `weekly`, `monthly`, `trigger-based`, `event-week`, `paused` |
| `last_checked` | last source check | `YYYY-MM-DD` |
| `next_check` | next planned check | `YYYY-MM-DD` |
| `monitoring_owner` | who owns monitoring | person/team |

## CRM Properties

Use these only when the card maps to CRM data.

| Property | Meaning |
| --- | --- |
| `hubspot_object_type` | `company`, `contact`, `deal`, `activity`, `ticket` |
| `hubspot_id` | HubSpot object ID |
| `crm_owner` | CRM owner |
| `crm_stage` | lifecycle/deal stage |
| `crm_last_synced` | last CRM read/sync date |

## Scoring Properties

| Property | Meaning |
| --- | --- |
| `score` | latest score |
| `score_band` | `hot`, `warm`, `nurture`, `low` |
| `score_confidence` | `high`, `medium`, `low` |
| `score_model` | link/name of scoring model |
| `scored_at` | score date |
| `next_review` | next score/review date |

## Source Properties

| Property | Meaning |
| --- | --- |
| `source` | source name |
| `source_id` | stable source item ID used in ledgers and evidence cards |
| `source_ids` | list of source IDs supporting an entity or conclusion |
| `raw_path` | immutable raw file path when the source is stored locally |
| `content_hash` | checksum/hash for raw files or normalized source content |
| `ingest_run_id` | ingest/research run that created or last processed the item |
| `url` | original URL |
| `canonical_url` | canonical normalized URL |
| `source_access_type` | access/licensing mode for the source itself |
| `date_published` | publication date |
| `date_collected` | collection date |
| `processed_status` | `queued`, `accepted`, `rejected`, `duplicate`, `superseded`, `needs-review` |
| `duplicate_of` | canonical source/card when duplicate |
| `corroborates` | claim IDs or cards supported |

## Edit Rules

- Agents can fill blank properties when evidence is strong.
- Agents must not overwrite non-empty controlled properties unless explicitly requested, CRM sync rules allow it, or review approves it.
- If a property value conflicts with evidence, add the proposed change to `Review Needed`.
