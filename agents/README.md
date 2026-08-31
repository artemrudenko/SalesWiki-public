# Agent Roles

These roles describe automations. They can be implemented as Codex skills, scheduled jobs, CRM/web hooks or manual operating modes.

A first executable implementation exists as Claude Code subagents in `.claude/agents/` (`research-orchestrator`, `lead-monitor`, `call-analyst`, `deal-risk`, `vault-linter`, `external-vault-import-assistant`, `connector-sync-planner`, `privacy-redaction-reviewer`, `event-research`) plus the `saleswiki-lead-scoring` skill, coordinated by the orchestration contract in `.claude/agents/README.md`. The roles below remain the conceptual reference.

## Research Agent

Finds and compiles company, market and executive updates from websites, open search and managed news resources.

Outputs:

- updated company/person/news pages
- source links
- suggested next actions

## Event Research Agent

Tracks exhibitions, conferences, webinars, summits and industry events.

Outputs:

- event brief
- exhibitors, sponsors, speakers and topics
- target account and competitor matches
- company/person page updates
- pre-event and post-event outreach suggestions

## Ingest Agent

Processes files dropped into `raw/imports/`, transcripts, CRM exports and research notes.

Outputs:

- normalized raw placement
- extracted entities
- updated wiki pages
- log entry

## External Vault Import Assistant

Guides a human through importing an existing team Markdown/Obsidian vault.

Outputs:

- read-only vault audit
- import scope menu
- proposed mapping from external folders/properties/tags to SalesWiki card types
- access and sensitive-data questions
- dry-run import plan for approval

## Call Analyst

Turns call transcripts into sales-useful knowledge.

Outputs:

- call summary
- pain points
- objections
- commitments
- deal and lead updates
- follow-up draft

## Deal Risk Agent

Checks active deals for stale activity, missing next steps, weak champions and negative signals.

Outputs:

- risk list
- reason
- recommended action
- owner

## Index Maintainer

Rebuilds and audits full-text, entity, graph, temporal and optional vector indexes.

Outputs:

- index status
- duplicate/orphan/stale reports
- system health updates

## Research Orchestrator

Plans and coordinates research tasks across specialized agents.

Outputs:

- task plan
- source list
- agent assignments
- deduplicated findings
- final cited brief
- wiki update checklist
