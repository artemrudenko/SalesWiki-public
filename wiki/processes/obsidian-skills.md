# Obsidian Skills Usage

SalesWiki uses Obsidian-first files as its durable system of record. The Obsidian skills from `kepano/obsidian-skills` are an agent assistance layer, not a replacement for SalesWiki governance.

## Installed Skills

Base project instructions are portable and live in the repository:

- `AGENTS.md` - default agent rules.
- `CLAUDE.md` - Claude Code project memory.
- `.claude/skills/saleswiki-obsidian/SKILL.md` - project-local Claude Code skill.
- `docs/AGENT_PORTABILITY.en.md` - handoff rules for different agent runtimes.

Use these external skills when available in the agent runtime:

- `obsidian-markdown` - writing and editing Obsidian Markdown, YAML properties, `[[wikilinks]]`, callouts, embeds and Mermaid diagrams.
- `obsidian-bases` - creating and maintaining `.base` dashboards for non-technical sales/marketing views.
- `json-canvas` - creating `.canvas` maps for account maps, event maps, campaign maps and system diagrams.
- `defuddle` - converting web pages into clean Markdown during research intake.
- `obsidian-cli` - optional interaction with a locally open Obsidian app.

## What These Skills Are For

Use them for:

- keeping cards compatible with Obsidian syntax
- creating readable dashboards for sales and marketing users
- turning source pages into clean raw/evidence Markdown
- creating visual relationship maps when a table is not enough
- validating that `.md`, `.base` and `.canvas` artifacts remain easy to open in Obsidian

Do not use them to bypass:

- `Controlled Profile` protection
- source tracking
- dedupe and corroboration
- access/redaction rules
- HubSpot read/propose/writeback boundaries
- health checks and git commits

## Skill-To-Workflow Mapping

| Workflow | Skill | Expected Output |
| --- | --- | --- |
| Create or update entity card | `obsidian-markdown` | Valid YAML properties, required sections, useful `[[wikilinks]]`. |
| Add dashboard for team use | `obsidian-bases` | `.base` file in `dashboards/` with filters, views and readable columns. |
| Build visual account/event map | `json-canvas` | `.canvas` file linked from the relevant Company/Event/Campaign page. |
| Process a web page | `defuddle` | Clean Markdown raw/evidence note plus URL/date/source metadata. |
| Inspect live vault state | `obsidian-cli` | Optional app-level check; never the only source of truth. |

## Dashboard Rules

Dashboards live in `dashboards/`.

Current dashboards:

- `dashboards/sales-today.base`
- `dashboards/lead-priority.base`
- `dashboards/deal-risk.base`
- `dashboards/review-queue.base`
- `dashboards/monitoring.base`
- `dashboards/marketing-insights.base`
- `dashboards/data-quality.base`

Rules:

1. Dashboards should read existing properties; do not invent new properties only for a view unless the property is added to `global-property-dictionary.md`.
2. A dashboard can hide noise, but it must not hide governance states like `access`, `freshness`, `confidence` or `profile_lock` when they affect action.
3. If a dashboard becomes a team workflow, link it from `README.md`, `wiki/index.md` and the relevant process page.
4. Treat `.base` files as views. The source of truth remains the card properties and body sections.
5. Markdown snapshots in `reports/dashboard-snapshots/` are generated from indexes with `scripts/build_dashboard_snapshots.py`; do not hand-edit them as source of truth.

Full dashboard rules: `wiki/processes/dashboard-contract.md`.

## Web Research Intake With Defuddle

When using `defuddle` or similar cleanup:

1. Keep the original URL and collection date.
2. Store or reference the cleaned output under the appropriate `raw/` folder.
3. Create or update an evidence card only after duplicate and source-quality checks.
4. Update `tracking/processed-sources.md` even for rejected pages.
5. If the page supports an important claim, update `tracking/corroboration-register.md`.

## Canvas Usage

Use `.canvas` files when a relationship is easier to understand visually than in a table.

Good candidates:

- account map: company, people, deals, calls, pains, tasks
- event map: event, sponsors, speakers, target accounts, competitors, outreach
- campaign map: insight, content brief, asset, campaign, channels, performance
- system map: raw, evidence, entities, actions, indexes

Canvas files should link back to the canonical Markdown cards. Do not store unique conclusions only in a canvas.

## Setup

Installation instructions are in:

- `docs/SETUP.en.md`

After installing skills, restart Codex so the runtime can load them.

## Maintenance

After changing dashboards, canvas maps or Obsidian-specific docs:

1. Check that linked properties exist in templates or `global-property-dictionary.md`.
2. Run `python3 scripts/health_check.py`.
3. Update `wiki/index.md` when a new reusable workflow artifact is added.
4. Commit the change.
