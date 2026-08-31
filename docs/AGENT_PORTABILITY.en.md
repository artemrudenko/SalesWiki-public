# Agent Portability

SalesWiki should work across different agent runtimes: Codex, Claude Code, Claude/Cowork-like tools and plain Obsidian without an agent.

## Main Principle

All critical rules live in the repository:

- `AGENTS.md` - main rule set for Codex and other agents that read AGENTS.md.
- `CLAUDE.md` - project memory for Claude Code.
- `.claude/skills/saleswiki-obsidian/SKILL.md` - project-local skill for Claude Code (vault conventions).
- `.claude/skills/saleswiki-lead-scoring/SKILL.md` - executable lead/deal scoring skill.
- `.claude/skills/saleswiki-scoring-configurator/SKILL.md` - user-approved scoring config changes.
- `.claude/agents/` - project subagents (`research-orchestrator`, `lead-monitor`, `call-analyst`, `deal-risk`, `vault-linter`, `external-vault-import-assistant`, `connector-sync-planner`, `privacy-redaction-reviewer`, `event-research`) plus the orchestration contract in `.claude/agents/README.md`.
- `agents/README.md` - runtime-agnostic conceptual agent roles.
- `docs/SETUP.en.md` - setup from scratch.
- `wiki/processes/` - business rules, governance, tracking, research and access rules.
- `wiki/processes/data-engineering-contract.md` - stable IDs, ingest runs, derived indexes and synthetic fixture rules.
- `wiki/processes/dashboard-contract.md` - required dashboards and Markdown snapshots.
- `wiki/processes/demo-vault.md` - separate synthetic vault for presentations.
- `wiki/processes/external-vault-import.md` - interactive import for existing vaults/folders.
- `wiki/processes/scoring-configuration.md` - rules for changing scoring weights/bands/penalties.
- `wiki/processes/connector-contracts.md` and `schemas/connector-contracts.json` - MCP/plugin/connector scopes, write modes and approvals.
- `wiki/processes/agent-orchestration.md` and `schemas/agent-routing.json` - skill/subagent routing and handoffs.
- `wiki/processes/event-research-profile.md` and `schemas/event-research-profile.json` - event-research scope, Playwright rules, action thresholds and pilot limits.
- `wiki/processes/browser-research-method-comparison.md` - staged-only comparison of `web-fetch`, `playwright-cli` and `webwright`.

Locally installed skills in `~/.codex/skills` or `~/.claude/skills` are enhancements, not required project files.

## What Happens When The Project Is Shared

If you share only the git repo:

- Markdown vault, templates, dashboards, health check and process docs are included.
- Index builder, dashboard snapshot builder, external-vault audit script, generated empty production indexes and synthetic test fixtures are included.
- `AGENTS.md`, `CLAUDE.md`, `.claude/skills/` and `.claude/agents/` are included.
- Globally installed skills from `kepano/obsidian-skills` are not included and must be installed again if needed.

## Codex

Codex should read `AGENTS.md`.

Recommended setup:

1. Open the repository.
2. Read `README.md` and `docs/SETUP.en.md`.
3. Install external Obsidian skills from `kepano/obsidian-skills` if needed.
4. Work according to `AGENTS.md`.
5. After changes, run `python3 scripts/health_check.py`; if real entity cards changed, run `python3 scripts/build_indexes.py` and, when needed, `python3 scripts/build_dashboard_snapshots.py`; then commit.

## Claude Code

Claude Code officially uses project memory from `CLAUDE.md` or `.claude/CLAUDE.md`. This project uses root `CLAUDE.md`, which imports `AGENTS.md`.

Claude Code can also use project skills from `.claude/skills/<skill>/SKILL.md` and subagents from `.claude/agents/<name>.md`. This repository includes:

- `.claude/skills/saleswiki-obsidian/SKILL.md`, `.claude/skills/saleswiki-lead-scoring/SKILL.md` and `.claude/skills/saleswiki-scoring-configurator/SKILL.md`
- subagents `research-orchestrator`, `lead-monitor`, `call-analyst`, `deal-risk`, `vault-linter`, `external-vault-import-assistant`, `connector-sync-planner`, `privacy-redaction-reviewer`, `event-research` (`.claude/agents/`)

That means the core SalesWiki logic and agent roles are available to Claude Code immediately after checkout, without external skill installation.

## Claude Cowork / Claude Desktop-like Workflows

If the tool can read project files, give it access to the SalesWiki root folder and ask it to start with:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `docs/SETUP.en.md`
4. `wiki/processes/obsidian-skills.md`

If the tool does not support project skills, it can still follow the Markdown documentation. External skills should be treated as optional.

## External Obsidian Skills

External skills from `kepano/obsidian-skills` are useful for:

- Obsidian Markdown
- Obsidian Bases
- JSON Canvas
- Defuddle web cleanup
- Obsidian CLI

They are installed separately on each machine. Instructions are in `docs/SETUP.en.md`.

## What To Maintain In The Repository

When changing agent setup, update:

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/skills/` (e.g. `saleswiki-obsidian`, `saleswiki-lead-scoring`)
- `.claude/agents/` (subagents + orchestration contract)
- `agents/README.md`
- `docs/SETUP.en.md`
- `wiki/processes/obsidian-skills.md`
- `wiki/processes/data-engineering-contract.md` when IDs, ingest runs or indexes change
- `wiki/processes/dashboard-contract.md` when dashboard/report rules change
- `wiki/processes/demo-vault.md` and `wiki/processes/external-vault-import.md` when demo/import workflows change
- `schemas/scoring-models.json`, `wiki/processes/scoring-configuration.md` and `state/scoring-change-requests.md` when scoring config changes
- `schemas/connector-contracts.json`, `schemas/agent-routing.json`, `wiki/processes/connector-contracts.md` and `wiki/processes/agent-orchestration.md` when connectors or agent routing change
- `schemas/event-research-profile.json` and `wiki/processes/event-research-profile.md` when event-research scope, collection methods or action thresholds change
- this document

Then run:

```bash
python3 scripts/health_check.py
```

If real entity cards changed, also run:

```bash
python3 scripts/build_indexes.py
```

If dashboard reports should be refreshed, also run:

```bash
python3 scripts/build_dashboard_snapshots.py
```
