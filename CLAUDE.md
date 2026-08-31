# SalesWiki Claude Project Memory

SalesWiki is an Obsidian-first sales and marketing wiki-brain, not a conventional software codebase. The durable source of truth is Markdown in this repository.

Claude Code should follow the shared agent rules in:

@AGENTS.md

Important onboarding docs:

@docs/SETUP.en.md
@wiki/processes/obsidian-skills.md

## Claude-Specific Notes

- Use project-local skill `.claude/skills/saleswiki-obsidian/SKILL.md` when working with SalesWiki Markdown, Obsidian Bases dashboards, Canvas maps, research intake, tracking or health checks.
- Use `.claude/skills/saleswiki-lead-scoring/SKILL.md` when scoring or re-scoring leads, MQLs or deals.
- Use `.claude/skills/saleswiki-scoring-configurator/SKILL.md` only when the user explicitly wants to change scoring weights, bands, penalties or default actions.
- Project subagents live in `.claude/agents/` (`research-orchestrator`, `lead-monitor`, `call-analyst`, `deal-risk`, `vault-linter`, `external-vault-import-assistant`, `connector-sync-planner`, `privacy-redaction-reviewer`, `event-research`); their orchestration, hand-offs and conflict rules are in `.claude/agents/README.md`.
- All `SKILL.md` files follow the open Agent Skills format (https://agentskills.io); `scripts/health_check.py` validates name/description/compatibility and spec-only frontmatter keys.
- The data-engineering contract lives in `wiki/processes/data-engineering-contract.md`: real cards need stable `entity_id`, `template_version`, `created` and `updated`; ingest/research runs are tracked in `state/ingest-runs.md`; derived indexes are rebuilt with `python3 scripts/build_indexes.py`. Identifier strategy is canonical in `wiki/processes/identifier-strategy.md` (opaque typed ULID core `<type>_<ULID>` minted once via `saleswiki_mcp/ids.py` into append-only `state/id-ledger.jsonl`, readable slug/alias surface, natural-key dedup; create production entity cards via the chokepoint `python3 scripts/new_entity.py`; the permissioned demo keeps deterministic readable slug ids by design; `health_check` validates the ledger when present).
- Dashboard contract lives in `wiki/processes/dashboard-contract.md`; Markdown snapshots are rebuilt with `python3 scripts/build_dashboard_snapshots.py`.
- Demo presentation data must follow `wiki/processes/demo-vault.md`; keep it outside production, mark it synthetic and regenerate with `python3 scripts/generate_demo_vault.py --reset`. Delivery-format demo digests are regenerated with `python3 scripts/generate_demo_digests.py`.
- Real pilot data follows `wiki/processes/pilot-data-contract.md`: the pilot vault (`dataset: pilot`) lives outside this repository; `health_check` (`check_pilot_boundary`) fails if a `pilot/` directory or `dataset: pilot` file appears inside the repo. The 5-minute first-run path is `docs/QUICKSTART.en.md` / `docs/QUICKSTART.ru.md`.
- External team vault imports must start with `wiki/processes/external-vault-import.md` and read-only `scripts/audit_external_vault.py`; `scripts/import_external_vault.py` may stage an approved package but must not blindly overwrite production cards.
- Scoring config is canonical in `schemas/scoring-models.json`; changes require `wiki/processes/scoring-configuration.md` and an entry in `state/scoring-change-requests.md`.
- Connector contracts are canonical in `schemas/connector-contracts.json`; review `wiki/processes/connector-contracts.md` before using MCP/plugins/connectors with real data.
- Agent routing is canonical in `schemas/agent-routing.json`; use `research-orchestrator` for multi-step workflows and handoffs.
- Event research is canonical in `schemas/event-research-profile.json`; use `wiki/processes/event-research-profile.md` for pilot limits, staged reports, Playwright collection rules and action thresholds.
- Browser method comparisons use `wiki/processes/browser-research-method-comparison.md`; keep `web-fetch` / `playwright-cli` / `webwright` comparisons staged-only until promotion approval.
- HubSpot card fill/writeback proposals go through `state/hubspot-writeback-proposals.md`; store HubSpot API keys and Webwright backend keys outside the repository.
- Use `wiki/processes/permission-boundary-blueprint.md` before sensitive ingest and `wiki/processes/file-drop-ingest-contract.md` for the first raw/imports ingest workflow.
- Permissioned-knowledge MVP is implemented under the `saleswiki_mcp/` package with canonical contracts `schemas/access-policy.json`, `schemas/boundary-registry.json` and `schemas/identity-provider.json` (validated by `scripts/health_check.py`). It exposes role-aware read/propose/govern tools, plus a separate single-writer `saleswiki_mcp/worker.py` that applies approved proposals to a card's Review Needed section under a lock with payload/base validation. The MCP gateway is read/propose only and never imports the worker; it needs the official `mcp` SDK via `requirements.txt` in a `.venv`; the vault, health check, indexes, core service and worker stay standard-library only. The single visual entry point + doc map is `docs/engineering/permissioned-knowledge-overview.md`; product rationale and roadmap are `docs/RATIONALE.en.md` and `docs/ROADMAP.en.md`. Read output is one Answer Contract envelope (`saleswiki_mcp/answer.py`: structured fields + rendered Markdown, tables for record lists, mandatory provenance, honest `not-found`); accuracy is by construction — the core extracts cited card values and never generates. Read extraction is decoupled from card shape via `schemas/field-extraction.json` (type→field→section/label), validated by health_check, so the gateway can serve a differently-shaped vault by swapping the profile (`docs/engineering/permissioned-knowledge-field-extraction.md`).
- The Rocket.Chat chat demo bridge (`integrations/rocketchat/`) is **optional**: it lets non-technical users talk to the permissioned vault from a chat channel (role switch by command, role-aware reads, the full governance loop). The primary interactive path to the permissioned vault is a Claude MCP client (Claude Code / Claude Desktop / Cowork) over the MCP gateway; the bridge is a demo surface, nothing else depends on it, and it runs only when started explicitly with `RC_*` credentials. Default mode imports the in-repo core (stdlib-only, no `.venv`); `RC_USE_MCP=1` routes through the real MCP server. Entry point and run/prereqs: `integrations/rocketchat/README.md`; design notes in `docs/engineering/permissioned-knowledge-overview.md` and `docs/engineering/permissioned-knowledge-access-requests.md`. Tests: `tests/test_rocketchat_bridge.py` + `tests/test_rocketchat_client.py`.
- Engineering docs about the software (permissioned MCP architecture, demo walkthroughs and extension designs) live under `docs/engineering/`, not `wiki/processes/`. `wiki/processes/` is the sales/marketing operating model. Place new engineering/architecture docs in `docs/engineering/`; see `docs/engineering/README.md`.
- Architecture Decision Records (the **why** behind product + engineering decisions) live in `docs/adr/` (index `docs/adr/README.md`). When making an architectural or cross-cutting decision (new boundary, authorization/schema/contract change, new card type, identity/deployment choice), add an ADR from `docs/adr/0000-template.md` and link it from the affected doc; supersede rather than rewrite an accepted ADR.
- Do not assume globally installed skills are present on a new machine.
- If external Obsidian skills from `kepano/obsidian-skills` are installed, use them as helpers, but keep SalesWiki governance from `AGENTS.md` authoritative.
- Run `python3 scripts/health_check.py` after structural documentation, template or dashboard changes.
- Run `python3 scripts/build_indexes.py` after creating, renaming, archiving, merging or materially relinking real entity cards.
- Run `python3 scripts/build_dashboard_snapshots.py` after index rebuilds when dashboard reports should be refreshed. `python3 scripts/refresh.py [--demo]` runs health check + indexes + snapshots as one command.
- Save completed repository changes with a git commit.
