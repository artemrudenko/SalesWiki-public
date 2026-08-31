# AGENTS.md - SalesWiki Wiki-Brain Rules

This file follows the [AGENTS.md](https://agents.md) open format: a README for coding/knowledge agents. Any AGENTS.md-compatible runtime (Codex, Claude Code, Cursor, etc.) should read it first. Human-facing docs live in `README.md` and `docs/`.

## Project overview

SalesWiki is an Obsidian-first sales and marketing wiki-brain, not a code project. The durable source of truth is Markdown in this repository: raw evidence in `raw/`, compiled knowledge cards in `wiki/`, derived indexes in `indexes/`, operational state in `state/` and `tracking/`. The whole folder opens directly as an Obsidian vault. New agents start with `README.md` and `docs/SETUP.en.md`.

## Setup commands

- Requires Python 3 for the health check, indexes and the permissioned core service; these use only the standard library, so there are no packages to install for them.
- The permissioned MCP gateway (`saleswiki_mcp/server.py`) additionally needs the official `mcp` SDK: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. It is optional and only required to run the MCP server; the vault and all checks work without it.
- Open the repository root as an Obsidian vault to use links, properties and graph view.
- Optional: install external Obsidian skills from `kepano/obsidian-skills` (see `docs/SETUP.en.md`). They are enhancements, not required.

## Build and test

There is no build step. The structural and data-model test is the health check; treat a non-zero exit as a failing test:

```bash
python3 scripts/health_check.py
```

It validates required files, raw dirs, dashboards, template frontmatter and required sections, duplicate `type`, enum values, real-card IDs/dates/score ranges, dashboard↔template property coherence, freshness coverage, duplicate doc links and dangling wikilinks in real cards. Expected clean result: `Errors: 0` and `Warnings: 0`.

Derived data indexes are rebuilt with:

```bash
python3 scripts/build_indexes.py
```

The indexes under `indexes/` are generated artifacts; rebuild them from Markdown rather than editing them by hand.

Dashboard snapshots are rebuilt with:

```bash
python3 scripts/build_dashboard_snapshots.py
```

Demo data is regenerated with:

```bash
python3 scripts/generate_demo_vault.py --reset
```

Health check, indexes and dashboard snapshots can run as one command (stops on the first failure):

```bash
python3 scripts/refresh.py            # production contour
python3 scripts/refresh.py --demo     # demo contour
```

Demo role digests (delivery-format `my_day` / `pipeline_risk_digest` artifacts under `demo/reports/digests/`) are regenerated with:

```bash
python3 scripts/generate_demo_digests.py
```

The permissioned-knowledge demo has an end-to-end smoke test (role contrast + no-leak, the governed write loop, reject path, audit chain, Answer envelope) that runs against a throwaway vault and exits non-zero on any failure:

```bash
python3 scripts/demo_dryrun.py
```

## Health Stack

- Python lint: `.venv/bin/ruff check saleswiki_mcp integrations/workbench scripts`
- Python tests: `python3 -m unittest discover -s tests`
- Workbench lint: `cd prototypes/knowledge-workbench && npm run lint`
- Workbench tests: `cd prototypes/knowledge-workbench && npm test`

## Testing instructions

- Run `python3 scripts/health_check.py` after any change to documents, templates, dashboards, properties, or the script itself.
- Run `python3 scripts/build_indexes.py` after creating, renaming, archiving, merging or materially relinking real entity cards.
- Run `python3 scripts/build_dashboard_snapshots.py` after rebuilding indexes when dashboards/reports need to reflect card changes.
- Use `wiki/processes/permission-boundary-blueprint.md` before ingesting real transcripts, CRM exports or contact/person data.
- Use `wiki/processes/file-drop-ingest-contract.md` for `raw/imports/` workflows until stronger connectors exist.
- Use `wiki/processes/external-vault-import.md` and read-only `scripts/audit_external_vault.py` before importing an existing team vault.
- Use `wiki/processes/demo-vault.md` for presentation data; demo cards must stay separate from production and be marked synthetic.
- Use `wiki/processes/pilot-data-contract.md` for the first real-data pilot: the pilot vault (`dataset: pilot`) lives outside this repository; `health_check` fails if a `pilot/` directory or `dataset: pilot` file appears inside the repo.
- Use `wiki/processes/connector-contracts.md` and `schemas/connector-contracts.json` before any MCP/plugin/connector touches real data.
- Use `wiki/processes/agent-orchestration.md` and `schemas/agent-routing.json` for multi-agent routing and handoffs.
- Use `wiki/processes/event-research-profile.md` and `schemas/event-research-profile.json` for conference/event research, Playwright collection limits and staged event reports.
- Use `wiki/processes/browser-research-method-comparison.md` for staged-only `web-fetch` / `playwright-cli` / `webwright` comparisons; do not promote results into production cards without separate approval.
- Use `state/hubspot-writeback-proposals.md` before filling or writing HubSpot card fields; no HubSpot API key or Webwright backend key may be stored in this repository.
- Keep `schemas/property-vocabularies.json` aligned with `wiki/processes/property-vocabularies.md` when enum values change.
- Assign entity ids only through the chokepoint `scripts/new_entity.py` (`create_entity`), which mints via `saleswiki_mcp/ids.py` (`IdAllocator.mint`) per `wiki/processes/identifier-strategy.md`: opaque typed ULID core `<type>_<ULID>`, minted once, deduped by natural key, recorded in append-only `state/id-ledger.jsonl`; never derive ids from mutable names or hand-author `entity_id`. The permissioned demo keeps deterministic readable slug ids by design. `health_check` validates the ledger when present.
- Use `docs/engineering/permissioned-knowledge-overview.md` (map), `docs/engineering/permissioned-knowledge-architecture.md` and `schemas/access-policy.json` / `schemas/boundary-registry.json` / `schemas/identity-provider.json` for the permissioned MCP MVP; run `python3 -m unittest discover -s tests` for the core (contracts, role-access, no-leak, prompt-injection, deal_risk, call_prep, lead_priority, event_brief, my_day, pipeline_risk_digest, marketing-workbench, role-tool matrix, approval, governance-inbox, worker-apply, redaction/dispatch, worker-transaction, worker-rollback, security/no-leak, end-to-end lifecycle, answer-contract) and `.venv/bin/python -m unittest discover -s tests` to also run the MCP-wiring test. The single-writer worker is `saleswiki_mcp/worker.py` (transactional apply, dead-letter queue, rollback); the gateway is read/propose only.
- Fix every `ERROR` before finishing a task; resolve `WARN` findings or state why they remain.
- When adding a new card type, update all six touch-points: the entity template, `wiki/processes/card-taxonomy.md`, `wiki/processes/property-vocabularies.md`, `wiki/index.md`, any relevant dashboard, and `REQUIRED_FILES` in `scripts/health_check.py` if it is a required doc.

## Commit guidelines

- Commit completed repository changes with a clear, imperative message describing what changed and why.
- Keep `raw/` evidence immutable; never rewrite source history.
- Do not commit local caches (`__pycache__/`, `*.pyc`); they are git-ignored.

## Project skills and agents

The repository ships an executable agent layer for Claude Code, with portable concepts for other runtimes:

- Skills (`.claude/skills/`): `saleswiki-obsidian` (vault conventions) and `saleswiki-lead-scoring` (executable V1 scoring).
- Scoring config skill (`.claude/skills/saleswiki-scoring-configurator`) is used only for explicit, user-approved scoring model changes.
- Subagents (`.claude/agents/`): `research-orchestrator`, `lead-monitor`, `call-analyst`, `deal-risk`, `vault-linter`, `external-vault-import-assistant`, `connector-sync-planner`, `privacy-redaction-reviewer`, `event-research`.
- Permissioned MCP service (`saleswiki_mcp/`): a separable core (identity, boundaries, RBAC+ABAC policy, retrieval, formatter, audit, append-only proposals) and an `mcp`-SDK stdio gateway exposing role-aware read/propose/govern tools (`company_brief`, `entity_graph`, `flag_stale_or_wrong`, `deal_risk`, `call_prep`, `lead_priority`, `event_brief`, `my_day`, `pipeline_risk_digest`, `campaign_brief`, `content_opportunities`, `request_redaction_review`, `request_access`, `approve_proposal`, `revoke_proposal`, `review_queue`, `get_proposal`, `reject_proposal`); a separate single-writer `saleswiki_mcp/worker.py` applies approved proposals transactionally (type registry, atomic validate-then-write so a failed apply never touches disk — no revert window, dead-letter queue, separate `worker.rollback`) and the gateway never imports it. Answer-style reads use the Answer Contract in `saleswiki_mcp/answer.py`; graph exploration uses the sibling `saleswiki.graph-view` v1 contract. Both are structured, cited, honest about `not-found`, and non-generative.
- Rocket.Chat chat demo bridge (`integrations/rocketchat/`), **optional**: lets non-technical users query the permissioned vault from a chat channel with role-aware reads and the full governance loop. The primary interactive path to the permissioned vault is a Claude MCP client (Claude Code / Claude Desktop / Cowork) over the MCP gateway; the bridge is a chat-channel demo surface and nothing else depends on it — it runs only when started explicitly with `RC_*` credentials. Default mode imports the in-repo core (stdlib-only, no `.venv`); `RC_USE_MCP=1` routes through the real MCP server. Entry point + run/prereqs: `integrations/rocketchat/README.md`. Tests: `tests/test_rocketchat_bridge.py`, `tests/test_rocketchat_client.py`.
- Knowledge Workbench BFF (`integrations/workbench/`), **optional and demo-only**: gives the browser one narrow read endpoint that invokes `saleswiki.entity_graph` through the official MCP stdio client. Actor, role, tool and vault remain server-owned; the bridge independently rejects non-demo vaults, and the UI labels the mode `Demo · fixed actor`. It is not SSO or a production remote MCP deployment. Run instructions: `docs/DEPLOYMENT.en.md`.
- Orchestration, hand-offs and conflict resolution: `.claude/agents/README.md`.
- Conceptual roles for any runtime: `agents/README.md`.

Skills are reusable procedures; subagents are roles that invoke them. All of them must obey the governance, citation, freshness and privacy rules in this file.

Every `SKILL.md` follows the open [Agent Skills](https://agentskills.io/specification) format: a `name` (lowercase, hyphenated, matching its directory) and a `description` of what it does and when to use it; optional `compatibility`, `license` and `metadata`; custom fields go under `metadata`. `scripts/health_check.py` validates this. New subagents use the Claude Code subagent format (`name`/`description`/`tools` frontmatter).

## Obsidian-first discovery

This project is primarily an Obsidian-compatible Markdown vault, not a codebase. Prefer Markdown navigation patterns over code graph tools:

1. Follow `[[wikilinks]]` and backlinks.
2. Use Obsidian Properties/YAML frontmatter for structured fields.
3. Use tags for broad filtering and properties for precise workflow state.
4. Use local search for raw files, source references and non-linked text.
5. Use derived indexes in `indexes/` only as acceleration, not as source of truth.

Do not use codebase-memory-mcp as the default discovery layer unless real application code is added later.

## Wiki-brain role

You are the maintainer of a sales and marketing LLM wiki. Your job is to turn raw sources into durable, linked, cited Markdown knowledge that can be queried by non-technical employees.

## Source of truth

- `raw/` stores immutable source material.
- `wiki/` stores compiled knowledge pages maintained by agents. `wiki/processes/` is the sales/marketing operating model (vault conventions, ingest, scoring, monitoring, governance) — not software docs.
- `docs/` stores human-facing docs: onboarding/reference (`SETUP`, `USER_GUIDE`, `ARCHITECTURE`, `AGENT_PORTABILITY`, `DEPLOYMENT`, `RATIONALE`, `ROADMAP`) and, under `docs/engineering/`, engineering docs about the permissioned MCP service. New engineering/architecture docs go in `docs/engineering/`, not `wiki/processes/`; see `docs/engineering/README.md`.
- `docs/adr/` stores Architecture Decision Records — the **why** behind significant product and engineering decisions (context, choice, consequences, rejected alternatives). When you make an architectural or cross-cutting decision (a new boundary, an authorization-model or schema/contract change, a new card type, an identity/deployment choice), add an ADR from `docs/adr/0000-template.md` and link it from the affected doc; supersede rather than rewrite. Index: `docs/adr/README.md`.
- `indexes/` stores derived indexes and graph exports. These can be rebuilt.
- `state/` stores operational status and audit traces.
- `tracking/` stores processed-source ledgers, dedupe decisions, corroboration links and coverage gaps.

The whole folder can be opened directly as an Obsidian vault.

Do not delete or rewrite raw evidence. If a source was wrong, add a correction note and link both the original and the correction.

## Required update loop

For every ingest, research, audit, or call analysis:

1. Save or reference the source in `raw/`.
2. Extract entities: companies, people, leads, deals, calls, products, competitors, signals, dates.
3. Update the relevant page in `wiki/entities/`.
4. Add cross-links using `[[Page Name]]` style where useful.
5. Update `wiki/index.md`.
6. Append a short entry to `wiki/log.md`.
7. Update the relevant tracking ledger when a source was checked, accepted, rejected or deduplicated.
8. Mark uncertain claims as `needs-source` or `low-confidence`.

For employee-provided links, people, companies, events, resources or topics, start with `state/manual-intake.md` and follow `wiki/processes/manual-intake.md`.

For recurring monitoring, use `sources/topic-monitors.md`, `sources/news-resources.md`, `sources/event-resources.md` and `state/monitoring-runs.md`.

After creating, renaming, archiving, merging or materially relinking pages, update `wiki/index.md` when needed and update `state/index-status.md` according to `wiki/processes/index-and-graph-maintenance.md`.

Research should be driven by `wiki/processes/sales-marketing-research-framework.md`: identify the user, decision moment, required output, freshness need and action before expanding the wiki.

Sales feedback priorities are captured in `wiki/processes/sales-team-feedback-requirements.md`. Prioritize lead monitoring/scoring, call analysis, KB/private case capture, HubSpot enrichment and HoS reporting before lower-priority event parsing automation.

Dashboards and generated snapshots are covered by `wiki/processes/dashboard-contract.md`. Demo presentation data is covered by `wiki/processes/demo-vault.md`. Existing departmental vault imports are covered by `wiki/processes/external-vault-import.md`.

Scoring weights, bands, penalties and default actions are canonical in `schemas/scoring-models.json`. Agents may apply scoring, but must not alter scoring configuration unless the user explicitly asks for a config change and the `wiki/processes/scoring-configuration.md` approval flow is followed.

Connector/MCP/plugin behavior is canonical in `schemas/connector-contracts.json`. Agent routing and handoffs are canonical in `schemas/agent-routing.json`. Event research output scope, action rules and pilot limits are canonical in `schemas/event-research-profile.json`.

## Obsidian conventions

- Use YAML properties at the top of wiki pages.
- Keep properties atomic: text, numbers, dates, checkboxes, lists and internal links.
- Keep long explanations, evidence and analysis in the body, not in properties.
- Put relationship links in the body as well as in properties when the relationship should appear clearly in the graph.
- Use tags like `#company`, `#person`, `#article`, `#lead`, `#deal`, `#call`, `#news`, `#event`, `#icp`, `#campaign`, `#needs-source`, `#stale`.
- Prefer stable page names: `Company - <Name>`, `Person - <Name>`, `Deal - <Company> - <Name>`, `Event - <Name>`.

## Obsidian skills

Base SalesWiki instructions are stored in this repository for portability:

- `CLAUDE.md` mirrors the project context for Claude Code and imports this file.
- `.claude/skills/saleswiki-obsidian/SKILL.md` is a project-local Claude Code skill.
- `docs/AGENT_PORTABILITY.en.md` describes how to hand the project to another agent environment.

When the local agent runtime has `kepano/obsidian-skills` installed, use the relevant skill for Obsidian-native artifacts:

- Use `obsidian-markdown` for `.md` cards, YAML properties, `[[wikilinks]]`, callouts, embeds and Mermaid diagrams.
- Use `obsidian-bases` for `.base` dashboards in `dashboards/`.
- Use `json-canvas` for `.canvas` account, event, campaign or system maps.
- Use `defuddle` when turning web pages into clean Markdown during research intake.
- Use `obsidian-cli` only as an optional live-Obsidian helper; the vault files remain the source of truth.

Follow `wiki/processes/obsidian-skills.md`. These skills improve Obsidian compatibility, but they do not replace source tracking, access/redaction rules, controlled-profile governance, health checks or git commits.

## Entity card governance

The canonical card-mutability contract (zones, `profile_lock`, the Fix Workflow routes and the Enforcement Map) is `wiki/processes/entity-card-governance.md`; this list is a summary.

- Treat `Controlled Profile` as protected identity/core metadata.
- Treat `Live Intelligence` as the normal update area for research, monitoring and analysis.
- Follow `wiki/processes/card-taxonomy.md`; cards of the same type must use the same required sections.
- Respect `profile_lock`.
- Do not overwrite non-empty controlled fields unless the user explicitly asks, a trusted sync source provides the value, or curator review approves it.
- Put proposed controlled-field changes in `Review Needed`.
- Do not delete entity cards during normal research.
- Prefer archive or duplicate-merge workflows over deletion.
- For delete/archive/merge/redact requests, use `state/deletion-requests.md` and `wiki/processes/deletion-and-archiving.md`.

## Citation rules

- Use source links or raw file paths for factual claims.
- Every news item needs: title, source, URL or raw path, publication date, collection date, affected entities.
- Every event item needs: event site/source, collection date, event date when available, participation type and affected companies/people.
- Every accepted or rejected article needs a tracking entry so future agents know it was already reviewed.
- Every call insight needs: call file/transcript path, call date, participants, analyst timestamp.
- Every deal insight needs: CRM source or explicit human note.

## Freshness rules

These are review-staleness windows. The canonical table reconciling review-staleness, score-decay and reminder-SLA is `wiki/processes/freshness-and-decay.md`; change thresholds there and keep this list in sync.

- Company profile: stale after 30 days without review.
- Company news: stale after 7 days for active deals, 30 days for watchlist accounts.
- Executive tracking: stale after 14 days for active target accounts.
- Hot leads: stale after 3 business days.
- Deal notes: stale after each meeting or material CRM change.

## Privacy and access

SalesWiki may contain personal data, call transcripts, lead information and commercial strategy. Keep private data in controlled files and avoid copying sensitive excerpts into broad summary pages unless needed for the business workflow.

Use these labels when relevant:

- `public`
- `internal`
- `sales-confidential`
- `personal-data`
- `legal-review`

## Answer style for employees

Prefer short, direct answers with:

- conclusion first
- why it matters
- newest facts first
- source dates
- confidence level
- recommended next action
- what is missing or stale

If the wiki lacks enough information, say what is missing and propose the smallest research task.
