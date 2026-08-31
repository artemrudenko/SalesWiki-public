# SalesWiki Index

Last updated: 2026-06-07

## Companies

- `wiki/entities/companies/_template.md` - template for company profiles.

## People

- `wiki/entities/people/_template.md` - template for CEO, CTO, founder, buyer, champion and influencer profiles.
- `wiki/entities/articles/_template.md` - template for authored articles, interviews, posts, talks and quotes.

## Leads

- `wiki/entities/leads/_template.md` - template for cold and warm leads.
- `wiki/entities/scoring-models/_template.md` - template for lead/deal scoring models.

## Deals

- `wiki/entities/deals/_template.md` - template for opportunities and deal state.
- `wiki/entities/account-plans/_template.md` - template for account strategy and stakeholder/action planning.
- `wiki/entities/products/_template.md` - template for products/offerings we sell (positioning, features, pricing, differentiation).
- `wiki/entities/customer-success/_template.md` - template for post-sale account health, adoption, renewal and expansion.

## Calls

- `wiki/entities/calls/_template.md` - template for transcript analysis and follow-up extraction.

## News

- `wiki/entities/news/_template.md` - template for company and executive news items.

## Events

- `wiki/entities/events/_template.md` - template for exhibitions, conferences and industry events.
- `wiki/entities/event-participation/_template.md` - template for company/person participation in an event.

## ICP And Segments

- `wiki/entities/icp/_template.md` - template for ideal customer profiles and target segments.
- `wiki/entities/buyer-personas/_template.md` - template for buyer roles and messaging.
- `wiki/entities/pain-points/_template.md` - template for reusable pain points.
- `wiki/entities/objections/_template.md` - template for objection handling.
- `wiki/entities/use-cases/_template.md` - template for sales/marketing use cases.
- `wiki/entities/competitor-intel/_template.md` - template for battlecards and competitor intelligence.
- `wiki/entities/case-studies/_template.md` - template for reusable proof and customer stories.
- `wiki/entities/private-cases/_template.md` - template for internal presales/delivery cases not ready for public use.
- `wiki/entities/outreach-sequences/_template.md` - template for outbound and nurture sequences.
- `wiki/entities/experiments/_template.md` - template for marketing/sales experiments.
- `wiki/entities/channels/_template.md` - template for marketing/sales channels.
- `wiki/entities/content-briefs/_template.md` - template for content briefs.
- `wiki/entities/content-calendar/_template.md` - template for content calendar items.

## Campaigns

- `wiki/entities/campaigns/_template.md` - template for marketing campaigns and performance learnings.

## Sources

- `sources/news-resources.md` - managed list of news resources and collection rules.
- `sources/event-resources.md` - managed event watchlist and event source rules.
- `sources/topic-monitors.md` - recurring topic monitoring definitions.
- `wiki/entities/sources/_template.md` - template for evaluating source quality.

## Supporting Entities

- `wiki/entities/topics/_template.md` - template for recurring market/product themes.
- `wiki/entities/claims/_template.md` - template for important claims supported by evidence.
- `wiki/entities/tasks/_template.md` - template for follow-up actions.
- `wiki/entities/assets/_template.md` - template for sales/marketing assets.
- `wiki/entities/enrichment-records/_template.md` - template for HubSpot/Apollo/Crunchbase enrichment proposals.
- `wiki/entities/reports/_template.md` - template for HoS and team reports.

## Processes

- `docs/SETUP.en.md` - setup from scratch, including Obsidian, health checks and agent skills.
- `docs/AGENT_PORTABILITY.en.md` - handoff guide for Codex, Claude Code and Claude/Cowork-like tools.
- `CLAUDE.md` - Claude Code project memory that imports `AGENTS.md`.
- `docs/ARCHITECTURE.en.md` - full architecture overview.
- `docs/USER_GUIDE.en.md` - employee user guide.
- `wiki/processes/ingest.md` - how new files and URLs enter the system.
- `wiki/processes/manual-intake.md` - how employee-provided links, people, companies and resources enter the system.
- `wiki/processes/research-and-audit.md` - how web research, company audit and freshness checks work.
- `wiki/processes/event-monitoring.md` - how to track exhibitions, speakers, sponsors, topics and participants.
- `wiki/processes/event-research-profile.md` - configurable event research profile, pilot limits, Playwright rules and output contract.
- `wiki/processes/event-roi-action-loop.md` - event outreach, meetings, pipeline impact and post-event review.
- `wiki/processes/research-agents.md` - recommended agent roles and research run contract.
- `wiki/processes/sales-marketing-research-framework.md` - user-centered research needs, decision moments, standardized outputs and employee request patterns (Query Playbook).
- `wiki/processes/sales-team-feedback-requirements.md` - sales-team feedback converted into requirements and priorities.
- `wiki/processes/lead-monitoring-and-scoring.md` - lead monitoring segments, cadences and scoring rules.
- `wiki/processes/marketing-attribution-and-content-workflow.md` - marketing attribution, channel, content and performance loop.
- `wiki/processes/reminder-and-task-workflow.md` - reminder, task, SLA and overdue rules.
- `wiki/processes/google-meet-call-import.md` - Google Meet recording/transcript import workflow.
- `wiki/processes/google-meet-participant-matching.md` - call participant identity matching and confidence rules.
- `wiki/processes/hubspot-enrichment.md` - HubSpot enrichment with Apollo/Open Web/Crunchbase workflow.
- `wiki/processes/private-case-capture.md` - dictated/written private case intake workflow.
- `wiki/processes/private-case-promotion-pipeline.md` - promotion path from private case to sanitized/internal/public case asset.
- `wiki/processes/stage-assistant.md` - sales assistant outputs by sales stage.
- `wiki/processes/scheduled-monitoring.md` - recurring collection and analysis workflow.
- `wiki/processes/tracking-dedupe-corroboration.md` - processed-source ledger, duplicate handling and evidence strength rules.
- `wiki/processes/source-governance.md` - source classes, reliability, access/licensing and usage rules.
- `wiki/processes/access-and-redaction-policy.md` - access labels, folder/vault policy and sanitized summary rules.
- `wiki/processes/global-property-dictionary.md` - canonical YAML properties and allowed values.
- `wiki/processes/property-vocabularies.md` - single source of truth for allowed property values per card type.
- `wiki/processes/permission-boundary-blueprint.md` - physical permission boundaries required before sensitive ingest.
- `wiki/processes/file-drop-ingest-contract.md` - first file-drop ingest contract for `raw/imports/` workflows.
- `wiki/processes/freshness-and-decay.md` - canonical review-staleness, score-decay and reminder-SLA thresholds.
- `wiki/processes/entity-card-governance.md` - controlled profile, live intelligence and card edit rules.
- `wiki/processes/relationship-model.md` - required links between companies, people, calls, articles, events, deals and conclusions.
- `wiki/processes/card-taxonomy.md` - standardized card types and required sections.
- `wiki/processes/data-engineering-contract.md` - stable IDs, ingest runs, derived indexes and synthetic fixture rules.
- `wiki/processes/dashboard-contract.md` - required operational dashboards and Markdown snapshot rules.
- `wiki/processes/demo-vault.md` - isolated synthetic demo-vault rules for presentations.
- `wiki/processes/pilot-data-contract.md` - where real pilot data lives (outside this repository) and the leak-prevention rules around it.
- `wiki/processes/external-vault-import.md` - human-in-the-loop import process for existing Markdown/Obsidian vaults.
- `wiki/processes/connector-contracts.md` - configurable MCP/plugin/connector scopes, write modes, approvals and audit logs.
- `wiki/processes/agent-orchestration.md` - configurable skill/subagent routing, handoffs and verification rules.
- `wiki/processes/browser-research-method-comparison.md` - staged-only comparison for `web-fetch`, `playwright-cli` and `webwright`.
- `wiki/processes/deletion-and-archiving.md` - deletion, archive, merge and permission workflow.
- `wiki/processes/index-and-graph-maintenance.md` - when and how indexes and graph exports are updated.
- `wiki/processes/hubspot-field-matrix.md` - CRM read/propose/writeback boundaries.
- `wiki/processes/hubspot-lifecycle-mapping.md` - HubSpot lifecycle/stage to SalesWiki segment/cadence/action mapping.
- `wiki/processes/scoring-models-v1.md` - starter inbound, outbound, MQL and deal scoring models.
- `wiki/processes/scoring-configuration.md` - user-approved scoring config change workflow.
- `wiki/processes/score-calibration.md` - scoring outcome feedback, score decay and recalibration workflow.
- `wiki/processes/kb-cleanup-and-drive-ingest.md` - Google Drive KB cleanup and ingest workflow.
- `wiki/processes/report-templates.md` - role-specific report formats for HoS, marketing, lead monitoring, campaign performance and data quality.
- `wiki/processes/graph-index.md` - graph, indexes and clustering design.
- `wiki/processes/obsidian-vault.md` - Obsidian-specific setup and conventions.
- `wiki/processes/obsidian-skills.md` - how agents should use Obsidian Markdown, Bases, Canvas, Defuddle and CLI skills.
- `wiki/processes/system-health.md` - monitoring, queues and quality checks.

## Engineering And Architecture

Engineering and implementation docs about the software itself (the permissioned MCP service and its architecture) live under `docs/engineering/`, not in `wiki/processes/`. `wiki/processes/` is the sales/marketing operating model; `docs/engineering/` is how the code is built. New engineering/architecture docs go here. See `docs/engineering/README.md`.

- `docs/engineering/permissioned-knowledge-overview.md` - single visual entry point and doc map for the permissioned-knowledge system.
- `docs/engineering/permissioned-knowledge-architecture.md` - multi-vault, MCP, role, approval, security and UX architecture for a permissioned SalesWiki knowledge service.
- `docs/engineering/permissioned-knowledge-field-extraction.md` - declarative card-shape decoupling profile for the read tools.
- `docs/engineering/permissioned-knowledge-demo.md` - end-to-end demo walkthrough (actors, structure, commands, diagrams).
- `docs/engineering/permissioned-knowledge-demo-runbook.md` - step-by-step demo runbook (commands and presenter script).
- `docs/engineering/permissioned-knowledge-pilot-runbook.md` - four-week lead_priority pilot on real data (seeding, weekly inflow, staleness measure, go/no-go).
- `docs/engineering/permissioned-knowledge-sso-design.md` - SSO / identity-provider integration design.
- `docs/DEPLOYMENT.en.md` - local and Docker starter path.
- `docs/RATIONALE.en.md` - public rationale and fit/non-fit boundaries.
- `docs/ROADMAP.en.md` - public preview roadmap.

## Agent Runtime Files

- `AGENTS.md` - default repo instructions for Codex-like agents.
- `CLAUDE.md` - Claude Code project memory.
- `.claude/skills/saleswiki-obsidian/SKILL.md` - project-local Claude Code skill for SalesWiki/Obsidian work.
- `.claude/skills/saleswiki-scoring-configurator/SKILL.md` - project-local skill for approved scoring model changes.
- `.claude/agents/research-orchestrator.md` - Claude Code subagent for request routing, handoffs, approvals and verification.
- `.claude/agents/external-vault-import-assistant.md` - Claude Code subagent for read-only external-vault audits and guided import planning.
- `.claude/agents/connector-sync-planner.md` - Claude Code subagent for connector/MCP/plugin planning.
- `.claude/agents/privacy-redaction-reviewer.md` - Claude Code subagent for access labels, redaction and sanitized-summary review.
- `.claude/agents/event-research.md` - Claude Code subagent for supervised event intelligence pilots.

## Config Schemas

- `schemas/scoring-models.json` - configurable lead/deal scoring weights, bands, penalties and default actions.
- `schemas/connector-contracts.json` - configurable connector/MCP/plugin scope, write modes, collection methods, approvals and audit logs.
- `schemas/agent-routing.json` - configurable skill/subagent routing, handoffs and verification.
- `schemas/event-research-profile.json` - configurable event-research outputs, source priorities, action rules and pilot limits.

## Dashboards

- `dashboards/sales-today.base` - Obsidian Bases view for daily sales actions across tasks, hot leads and risky deals.
- `dashboards/lead-priority.base` - Obsidian Bases view for hot/warm leads and outside-pipeline watchlist.
- `dashboards/deal-risk.base` - Obsidian Bases view for stale, low-score or CRM-sync deal risk.
- `dashboards/review-queue.base` - Obsidian Bases view for cards that need review, sources or confidence cleanup.
- `dashboards/monitoring.base` - Obsidian Bases view for monitored companies, people, events, topics and sources.
- `dashboards/marketing-insights.base` - Obsidian Bases view for topics, pains, objections, briefs and campaign ideas.
- `dashboards/data-quality.base` - Obsidian Bases view for missing sources, low confidence and access-review items.
- `reports/dashboard-snapshots/` - generated Markdown dashboard reports for presentations and quick review.

## Tracking

- `tracking/processed-sources.md` - source URLs/files already reviewed.
- `tracking/dedupe-register.md` - duplicate and near-duplicate decisions.
- `tracking/corroboration-register.md` - claims confirmed by multiple sources.
- `tracking/coverage-gaps.md` - people, events, companies and topics not yet checked.
- `state/manual-intake.md` - queue for manual employee requests.
- `state/monitoring-runs.md` - log of scheduled and manual monitoring runs.
- `state/ingest-runs.md` - run ledger for imports, research sweeps, CRM exports and synthetic fixture tests.
- `state/access-review.md` - queue for access-label changes, redaction approvals and personal-data sharing decisions.
- `state/hubspot-writeback-proposals.md` - queue for proposed HubSpot card fills, field updates and task writebacks.
- `state/deletion-requests.md` - queue for delete, archive, merge and redact requests.
- `state/index-status.md` - current status of derived indexes.
- `state/score-feedback.md` - scoring outcome feedback for calibration.

## Scripts

- `scripts/health_check.py` - structural and data-quality health check for required files, raw folders, entity frontmatter, enums, IDs and required sections.
- `scripts/build_indexes.py` - derived index builder for entity registry, freshness, temporal, graph and full-text inventories.
- `scripts/build_dashboard_snapshots.py` - generated Markdown dashboard reports from indexes.
- `scripts/audit_external_vault.py` - read-only external Markdown/Obsidian vault audit for import planning.
- `scripts/import_external_vault.py` - dry-run planner and approved staging executor for external vault imports.
- `scripts/generate_demo_vault.py` - regenerates isolated synthetic demo data under `demo/`.
