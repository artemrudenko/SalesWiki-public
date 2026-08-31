# SalesWiki Subagents (executable)

These are project-local Claude Code subagents — the executable, first implementation of the conceptual roles described in `../../agents/README.md`. They are starter versions: scoped, governed, and meant to be hardened with real usage.

## Skills vs. agents (division of labour)

- **Skills** (`.claude/skills/`) are reusable *procedures/knowledge* — e.g. `saleswiki-lead-scoring` (how to score), `saleswiki-scoring-configurator` (approved scoring config changes), `saleswiki-obsidian` (vault conventions). Invoked from any context.
- **Subagents** (`.claude/agents/`) are *roles* with a tool scope that *use* skills to run a task end-to-end and return a structured result.

This separation exists on purpose: scoring execution reads `schemas/scoring-models.json`; `lead-monitor`, `deal-risk` and `call-analyst` apply it instead of restating weights. Scoring configuration changes use the separate configurator flow and require user approval.

## The subagents

| Subagent | Role | Maps to conceptual role |
| --- | --- | --- |
| `research-orchestrator` | route complex requests, coordinate handoffs, enforce approvals | Research Orchestrator |
| `lead-monitor` | re-score + surface action-worthy leads, create tasks | Research Agent (lead side) |
| `call-analyst` | transcript → call card + extractions + propagation | Call Analyst |
| `deal-risk` | audit active deals for risk | Deal Risk Agent |
| `vault-linter` | structural + data-model integrity, health check | Index Maintainer |
| `external-vault-import-assistant` | read-only audit + guided import planning/staging for existing vaults | Ingest Agent |
| `connector-sync-planner` | connector/MCP/plugin scope, approval and writeback planning | Connector Planner |
| `privacy-redaction-reviewer` | access labels, redaction and sanitized-summary review | Privacy Reviewer |
| `event-research` | supervised event intelligence pilots, event-account matching and event ROI research | Event Research Agent |

Event Research is active for supervised pilots. It defaults to staged reports and requires approval before production card creation, outreach task creation or high-volume browser collection.

## Orchestration contract

When more than one agent runs (e.g. a weekly sweep), `research-orchestrator` follows this contract:

1. **Shared output schema.** Every agent returns: `conclusion` (one line), `items[]` (each with entity link, evidence links + dates, confidence, recommended action, owner), `gaps[]`, and `cards_changed[]`.
2. **Handoffs.** `call-analyst` finishing a call → triggers a re-score handoff to `lead-monitor`/`deal-risk` for the linked lead/deal. `lead-monitor` and `deal-risk` emit tasks to `state/queues.md`. `external-vault-import-assistant` creates approved staging packages and hands mapped card creation to a curator/orchestrator. `event-research` creates staged event reports first and hands strong target-account signals to `lead-monitor` only after review. `connector-sync-planner` checks connector scope before any MCP/plugin use. `privacy-redaction-reviewer` runs before sensitive sharing. `vault-linter` runs last as the integrity gate.
3. **Deduplication.** Before writing, check `tracking/processed-sources.md` and `dedupe-register.md`; merge findings about the same entity rather than creating parallel notes. Independent confirmations strengthen `confidence` (see `tracking-dedupe-corroboration.md`).
4. **Conflict resolution.** If two agents disagree on a value: HubSpot wins for stage/owner/next-activity; most-recent dated evidence wins for facts; if still unresolved, write both to `Review Needed` with sources and do not silently pick one.
5. **Confidence.** Carry `high|medium|low` through merges; a merged claim is no more confident than its best single source unless corroborated.
6. **Data contract.** Preserve stable `entity_id`, `template_version`, source lineage fields and `ingest_run_id` per `wiki/processes/data-engineering-contract.md`. After real card creation, rename, archive, merge or material relinking, rebuild indexes with `python3 scripts/build_indexes.py` and refresh dashboard snapshots with `python3 scripts/build_dashboard_snapshots.py` when reports need to reflect the change.

## Governance (applies to every agent)

- Respect `AGENTS.md`: don't overwrite controlled-profile fields or raw evidence; propose controlled changes in `Review Needed`.
- HubSpot remains CRM source of truth.
- Update `tracking/` ledgers for sources reviewed.
- Run `python3 scripts/health_check.py` after edits; rebuild indexes when real entity cards changed; refresh dashboard snapshots when operational reports changed; commit only when asked.
