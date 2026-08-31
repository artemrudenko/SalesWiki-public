# Hooks And Automations

Hooks are future integration points for keeping SalesWiki current.

## File Drop Hook

Trigger: new file in `raw/imports/`.

Action:

- classify source
- move or reference it under the right raw folder
- run ingest
- update wiki/log/index

## Web Research Hook

Trigger: scheduled account audit or employee research request.

Action:

- check company-owned sources
- search managed news resources
- run open web search
- update company, people and news pages

## Manual Intake Hook

Trigger: employee asks to review a link, add a person/company, analyze a material, or start monitoring a topic.

Action:

- add request to `state/manual-intake.md`
- classify intake type
- check processed-source tracking
- create or update wiki pages
- update watchlists if monitoring is requested

## Scheduled Monitoring Hook

Trigger: recurring schedule, for example Monday 06:00 collection and Monday 09:00 analysis.

Action:

- run raw collection against configured sources and topics
- record run in `state/monitoring-runs.md`
- update tracking ledgers
- run later analysis over collected items
- publish short report with changes, duplicates, corroborated claims and follow-up tasks

## CRM Sync Hook

Trigger: CRM export or API event.

Action:

- update leads and deals
- flag stale or high-priority records
- preserve CRM as source reference

## Call Transcript Hook

Trigger: new transcript in `raw/calls/`.

Action:

- summarize call
- extract commitments, pains, objections and buying signals
- update company, lead and deal pages

## Index Rebuild Hook

Trigger: wiki page changed.

Action:

- rebuild full-text/entity index
- update graph edges
- refresh system health state

Important:

- Obsidian graph updates inside Obsidian from Markdown links.
- Derived indexes under `indexes/` should be rebuilt or marked stale after entity creation, rename, archive, merge, deletion request, relationship changes or scheduled analysis runs.
- Track derived index state in `state/index-status.md`.

## Deletion/Archive Hook

Trigger: curator/admin approves delete, archive, merge or redact request.

Action:

- update entity `deletion_status`
- preserve or update backlinks
- update dedupe/tracking records
- update `wiki/index.md`
- rebuild or mark indexes stale
- append result to `wiki/log.md`

## Alert Hook

Trigger examples:

- hot lead without next action
- active deal stale
- CEO/CTO news on target account
- negative company news
- source failure

Action:

- create digest item or notification for the relevant owner
