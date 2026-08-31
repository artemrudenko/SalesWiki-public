# SalesWiki Setup From Scratch

This document describes how to set up SalesWiki as an Obsidian vault and as an agent-assisted workspace.

For the shortest first-value path (demo data, MCP questions, one-command
verification) start with [DEMO.en.md](DEMO.en.md) or
[QUICKSTART.en.md](QUICKSTART.en.md) and come back here for the full setup.

For local vs Docker runtime details, see [DEPLOYMENT.en.md](DEPLOYMENT.en.md).

## Required Tools

Required:

- Git — to clone, diff and save changes.
- Python 3.11+ — for health checks, index builders, tests and the permissioned
  core service. Docker uses Python 3.12.
- A POSIX-like shell — for the documented commands.

Recommended:

- Obsidian — to open the folder as a vault and use `[[wikilinks]]`, properties,
  graph view and `.base` dashboards.
- Docker Desktop or Docker Engine with Compose V2 — for repeatable isolated
  checks and demo runs.
- Python virtual environment support (`python3 -m venv`) — required for the
  MCP gateway and full test suite.

Optional:

- Claude Desktop / Claude Code / Cowork or another MCP client — to call the
  permissioned gateway.
- Codex or another agent runtime — for research, analysis, card updates and
  automations.
- Node.js/npm — only if you want to install external Obsidian skills through
  `npx skills`.
- Obsidian CLI — if the agent should interact with the open Obsidian app.

## Get The Project

```bash
git clone <repo-url> SalesWiki
cd SalesWiki
python3 scripts/first_run.py
```

`first_run.py` creates `.venv`, installs `requirements.txt`, runs the public
release review, validates the vault and runs the permissioned demo smoke test.
Use `python3 scripts/first_run.py --full-tests` when you also want the full
unit test suite.

If the folder already exists locally:

```bash
cd /path/to/SalesWiki
git status
```

If you will commit from this machine, configure your name and email once:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Open The Vault In Obsidian

1. Open Obsidian.
2. Choose `Open folder as vault`.
3. Select the root `SalesWiki` folder.
4. Start with `README.md`, `docs/USER_GUIDE.en.md` and `wiki/index.md`.

## Verify Structure

```bash
python3 scripts/health_check.py
```

Expected result:

```text
SalesWiki health check
Errors: 0
Warnings: 0
```

The health check also validates scoring config (`schemas/scoring-models.json`), connector/agent/event configs and the demo/production boundary.

## Build Derived Indexes

Run this after creating, renaming, archiving, merging or materially relinking real entity cards:

```bash
python3 scripts/build_indexes.py
```

The script rebuilds machine-readable artifacts in `indexes/` and updates `state/index-status.md`. Generated index files are derived from Markdown and should not be edited by hand.

Synthetic fixtures can validate non-empty output without touching production state:

```bash
python3 scripts/build_indexes.py --source-root tests/fixtures/synthetic-vault --output-root /tmp/saleswiki-fixture-indexes --no-update-state
```

To validate expected fixture row counts:

```bash
python3 scripts/build_indexes.py --source-root tests/fixtures/synthetic-vault --output-root /tmp/saleswiki-fixture-indexes --no-update-state --expect-counts tests/fixtures/expected-index-counts.json
```

## Build Dashboard Snapshots

Markdown snapshots provide simple reports without Obsidian Bases and are useful for presentations or weekly review:

```bash
python3 scripts/build_dashboard_snapshots.py
```

Production snapshots are written to `reports/dashboard-snapshots/`. For a demo vault or test fixtures, pass separate `--index-root` and `--output-root` values so datasets do not mix, and pass `--vault-root` (the folder the cards live in) so the snapshot's card links resolve from its own location.

## Configure Scoring

Starter weights and thresholds live in `schemas/scoring-models.json`. They may be changed only after explicit user approval through `wiki/processes/scoring-configuration.md`; proposals and decisions are tracked in `state/scoring-change-requests.md`.

## Install Obsidian Skills For The Agent

SalesWiki works without external skills because the basic rules live in the repository:

- `AGENTS.md` - for Codex and AGENTS.md-aware agents.
- `CLAUDE.md` - project memory for Claude Code.
- `.claude/skills/saleswiki-obsidian/SKILL.md` - project-local Claude Code skill.

External skills are useful as an additional layer: they help the agent keep Obsidian Markdown, `.base` dashboards, `.canvas` maps and web-to-Markdown extraction consistent.

Install through the Codex skill installer:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo kepano/obsidian-skills --path skills/obsidian-markdown skills/obsidian-bases skills/json-canvas skills/obsidian-cli skills/defuddle
```

Restart Codex after installation so the new skills are loaded.

Alternative through npm, if your environment uses the `skills` CLI:

```bash
npx skills install https://github.com/kepano/obsidian-skills
```

Used skills:

- `obsidian-markdown` - Obsidian Markdown, properties, `[[wikilinks]]`, callouts and Mermaid.
- `obsidian-bases` - `.base` dashboards for sales/marketing views.
- `json-canvas` - visual account/event/campaign maps.
- `defuddle` - web page cleanup into Markdown for research.
- `obsidian-cli` - optional integration with the open Obsidian app.

Detailed rules: `wiki/processes/obsidian-skills.md`.

## Setup For Different Agents

Codex:

1. Open the repository.
2. Codex should use `AGENTS.md`.
3. External Obsidian skills can be installed with the command above.

Claude Code:

1. Open the repository in Claude Code.
2. Claude Code will read `CLAUDE.md`.
3. The project-local skill is in `.claude/skills/saleswiki-obsidian/SKILL.md`.
4. External Obsidian skills can be installed separately, but the basic logic is already in the repo.

Claude Cowork / Claude Desktop-like tools:

1. Give the tool access to the SalesWiki root folder.
2. Ask it to start with `CLAUDE.md`, `AGENTS.md` and `docs/SETUP.en.md`.
3. If project skills are not supported, use the Markdown docs as instructions.

Details: `docs/AGENT_PORTABILITY.en.md`.

## Connector And Agent Routing Config

Before enabling an MCP/plugin/connector, check:

- `schemas/connector-contracts.json` - read scopes, write modes, collection methods, approvals, forbidden operations and audit logs.
- `schemas/agent-routing.json` - which skill/subagent owns each request type, handoffs and verification.
- `schemas/event-research-profile.json` - event-research source priorities, pilot limits, Playwright/Webwright rules and action thresholds.

The health check validates these files.

Full Webwright harness requires an external backend key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY`). Do not store keys in the repository. Without a key, Webwright is used only as an artifact contract: `plan.md`, `final_script.py`, screenshots, logs and structured output.

## Obsidian Bases Dashboards

The `dashboards/` folder contains required `.base` views:

- `dashboards/sales-today.base` - what to do today: overdue/due tasks, hot leads and risky deals.
- `dashboards/lead-priority.base` - hot and warm leads.
- `dashboards/deal-risk.base` - risky deals and stale/CRM sync signals.
- `dashboards/review-queue.base` - cards that require review or have low confidence.
- `dashboards/monitoring.base` - companies, people, events, topics and sources under monitoring.
- `dashboards/marketing-insights.base` - topics, pains, objections and content/campaign opportunities.
- `dashboards/data-quality.base` - missing sources, low confidence and access-review items.

If Obsidian does not render `.base` as a table, update Obsidian and check that Bases are available in your installation. The files remain plain text and are not the source of truth.

Dashboard rules are documented in `wiki/processes/dashboard-contract.md`.

## Demo Vault

For a sales/marketing demo, use a separate synthetic vault instead of production cards. Contract: `wiki/processes/demo-vault.md`.

Recommended structure:

```text
demo/demo-vault/
demo/indexes/
demo/reports/
```

Demo cards must use `dataset: demo`, `synthetic: true` and an `entity_id` that starts with `demo-`. This data can be added, regenerated and deleted without extra approvals as long as it stays separate from production.

Regenerate the demo:

```bash
python3 scripts/generate_demo_vault.py --reset
python3 scripts/build_indexes.py --source-root demo/demo-vault --output-root demo/indexes --no-update-state
python3 scripts/build_dashboard_snapshots.py --index-root demo/indexes --output-root demo/reports/dashboard-snapshots --vault-root demo/demo-vault
```

## Import An Existing Vault

If a department already has its own Obsidian/Markdown vault, start with a read-only audit:

```bash
python3 scripts/audit_external_vault.py --source /path/to/external-vault --output /tmp/saleswiki-import-audit.md
```

The interactive `external-vault-import-assistant` then guides the user through audit, scope selection, mapping, import plan, approval and execution. Production files are not changed before approval. The process is documented in `wiki/processes/external-vault-import.md`.

Dry-run plan:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault
```

Approved staging after scope/mapping selection:

```bash
python3 scripts/import_external_vault.py --source /path/to/external-vault --run-id external-vault-YYYYMMDD --execute
```

## First Working Loop

1. A user adds a request to `state/manual-intake.md`.
2. The agent checks `tracking/processed-sources.md`.
3. Raw material is stored or referenced under `raw/`.
4. A card is created or updated in `wiki/entities/`.
5. `[[wikilinks]]`, evidence, confidence and tracking are added.
6. When needed, `dashboards/`, `wiki/index.md`, `state/index-status.md` and `wiki/log.md` are updated.
7. Run `python3 scripts/health_check.py`.
8. If real entity cards changed, run `python3 scripts/build_indexes.py`.
9. After rebuilding indexes, create dashboard snapshots with `python3 scripts/build_dashboard_snapshots.py`.
10. Save changes with a git commit.

## What Is Not A Dependency

- There is no required database.
- There are no required Python packages for the vault, health check, indexes or the permissioned core; only the optional MCP gateway needs the `mcp` SDK (`requirements.txt`).
- Obsidian graph is built by Obsidian from Markdown links.
- `indexes/` and `.base` dashboards are derived acceleration layers, not the primary source of truth.
- Test fixtures under `tests/fixtures/` are synthetic and may be regenerated or deleted without approval.

## Troubleshooting

- Health check fails: fix missing files, raw folders, YAML properties or required template sections first.
- `.base` does not render: open it as Markdown/YAML or update Obsidian.
- Agent does not see Obsidian skills: restart Codex after installation.
- Data is sensitive: follow `access-and-redaction-policy.md` and do not copy personal data into broad summary pages.
- Docker check fails: run the same command locally first, then check
  [DEPLOYMENT.en.md](DEPLOYMENT.en.md) for which service failed.
