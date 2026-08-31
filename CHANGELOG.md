# Changelog

All notable changes to SalesWiki are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
SalesWiki is pre-1.0: minor (`0.x.0`) bumps mark milestone releases and may
include breaking changes to schemas, contracts or tool surfaces.

Versions are tagged in git (`git tag`); each heading links the milestone to the
commit it was cut from.

## [Unreleased]

### Added
- **Guided Workbench tours**: the synthetic Workbench now offers a full product
  tour and role-specific tours. They navigate real demo states, highlight the
  active UI and explain role-scoped priorities, cited assistant answers and
  governed review without writing any data.

### Security & hardening (post-review)
- **Fail-closed default boundary**: a card outside every `path_map` prefix now
  resolves to a `quarantine` boundary no role can read (was world-readable
  `broad`); `health_check` flags any such misfiled card.
- **`card_xray` role-gated**: the "behind the glass" reveal no longer lists
  closed-zone card names to roles without access (names are themselves sensitive);
  it still teaches that a zone exists and which role unlocks it.
- **Audit hash-chain race fixed**: the append is now a single-lock
  read-modify-write with flush+fsync before unlock, so concurrent writers cannot
  break the tamper-evident chain.
- **Signed audit checkpoints**: a deployment-only HMAC checkpoint can protect a
  verified log prefix from clean tail deletion; it must live outside the runtime
  volume and refuses to advance after a failed verification.
- **Worker apply** validates in memory and writes atomically (temp + `os.replace`),
  with an idempotency guard against double-apply on the empty-`base_hash` path.
- **`clear`/`очистить`** matched by exact command forms (no longer swallows
  "clearance …").
- **Docs**: Rocket.Chat bridge now referenced from README / QUICKSTART /
  USER_GUIDE / CLAUDE.md / AGENTS.md; stale tool/test counts corrected.
- **Tests** added for the RocketChat client, apply error paths, boundary
  fail-closed, audit concurrency, worker atomicity and malformed cards.

- Pending: full interactive walkthrough in Rocket.Chat and fast-forward merge of
  `rocketchat-bridge` into `main`.

## [0.4.0] - 2026-06-17 — Chat demo bridge & governed access

A chat-first demo: employees query the permissioned vault from Rocket.Chat and
get role-aware, cited answers over a synthetic demo vault, with the full
governance loop driven from chat.

### Added
- **Rocket.Chat demo bridge** (`integrations/rocketchat/bridge.py`, stdlib-only):
  ask the permissioned vault from chat with a `?` trigger; in-chat role switching
  (`role: …`) drives role-aware access (self-asserted — demo only, SSO is the prod story).
- **Governed access lifecycle**: `request_access` → review → approve → live,
  time-boxed, scoped grant → revoke/expiry; plus `flag-stale` and `redaction`
  propose types, and a chat-driven propose → approve → **apply** loop run by the
  separate single-writer worker.
- **Synthetic Google Drive connector**: list a connected folder, turn a file into
  a governed `ingest_resource` proposal (no OAuth/network); folder visibility is
  no-leak by role.
- **Demo "reveal" commands**: `card <company>` (full source-of-truth by zone),
  `how it works` (card lifecycle), `demo` / `demo <role>` scenario catalogue,
  `clear history`, `.md`/`.csv` file upload, and an ASCII access chart.
- **`🤖 Summary` header** on read answers, built strictly from the cited envelope
  (deterministic by default; opt-in real LLM via `RC_LLM_SUMMARY`).
- **Numeric scores + quantified pipeline rollup** (deal Score / Win % / Value,
  weighted pipeline, by-stage) across the demo cards and tools.
- Optional **dual backend**: in-process core (default) or the real MCP server (`RC_USE_MCP`).
- One-shot **live smoke test** (`integrations/rocketchat/smoke_test.py`); live
  round-trip verified against a self-hosted Rocket.Chat 7.10.

### Changed
- **All bridge output is English** (no Russian/English mix); command input stays
  bilingual (RU + EN) so existing phrasings still route.
- **Answer UX**: every `🔒` names the role that unlocks the data; the pipeline is
  an honest `aggregated` view for roles without deal access (no false-empty);
  friendly section headings (internal zone prefixes stripped); sources deduped,
  one per line; blank lines before the footer; meaningful brief conclusions.
- **Demo data enriched** with explicitly-synthetic LLM-origin detail (signal
  detection metadata, call-analyst extraction, lead scoring factors + activity).

### Fixed
- `my_day` doubled section headers and the "Linked deal" cell stutter.
- ABAC ownership masking was mislabelled as "only personal-data withheld".
- Type-aware approval in MCP mode (flag/redaction no longer claim "access granted").
- README duplicate link → `health_check` is now `Errors: 0, Warnings: 0`.

## [0.3.0] - 2026-06-09 — Deployment design, demo enrichment & pilot contour

### Added
- Deployment + SSO design docs; boundary-storage decision (ACL folder + external
  personal-data).
- Pilot data contract / first-real-data contour outside the repo; lowered the
  first-steps barrier; consolidated permissioned-knowledge demo walkthrough (EN/RU)
  and demo runbook.
- Enriched permissioned demo with market signal, sanitized proof and competitor intel.

### Changed
- Moved engineering/implementation docs to `docs/engineering/`; `wiki/processes/`
  stays the sales/marketing operating model.
- Consolidated access docs into one policy; broadened the README process index.

### Fixed
- Documentation drift: stale refs, missing index entries, categorization/labels,
  cross-links and canonical-source pointers.

## [0.2.0] - 2026-06-04 — Permissioned knowledge MVP

The permissioned MCP service shipped as ten value-first vertical slices, plus an
architecture-hardening and accuracy pass.

### Added
- **Permissioned MCP service** (`saleswiki_mcp/`): a separable core (identity,
  boundaries, RBAC+ABAC policy, retrieval, formatter, audit, append-only proposals)
  and an `mcp`-SDK stdio gateway.
- **Role-aware read tools**: `company_brief`, `deal_risk`, `call_prep`,
  `lead_priority`, `event_brief`, `my_day`, `pipeline_risk_digest`, `campaign_brief`,
  `content_opportunities` — with full role coverage and a role × tool matrix.
- **Governance**: propose (`flag_stale_or_wrong`, `request_redaction_review`,
  `request_access`), approval lifecycle + approver RBAC, and a Curator/RevOps
  inbox (`review_queue`, `get_proposal`, `reject_proposal`).
- **Single-writer worker**: transactional apply, dead-letter queue and rollback;
  the gateway is read/propose only and never imports it.
- **Answer Contract** envelope (structured fields + Markdown, mandatory provenance,
  honest `not-found`, no generation) and a **field-extraction contract** that
  decouples read extraction from card shape.
- **Identifier strategy**: opaque typed-ULID allocator + append-only ledger, with
  an entity-creation chokepoint (`scripts/new_entity.py`).
- `scripts/demo_dryrun.py` end-to-end smoke test, a Go/No-Go readiness checklist,
  and a documented security/no-leak review (fail-safe boundary gate + E2E).
- Product/Offering and Customer Success entity types.

### Changed
- Architecture hardening: referential / ownership / boundary integrity checks,
  strict entity resolution, data-derived freshness, crash-safe lock, robust JSONL
  parsing, tamper-evident audit chain, and write-governance split out of the
  former god-class.
- Permissioned demo cards reshaped to match production templates.

## [0.1.0] - 2026-05-30 — Wiki-brain foundation

### Added
- Obsidian-first vault foundation: typed sales/marketing entity templates, a
  unified card schema, Bases dashboards, canonical vocabulary docs and a
  `health_check` linter.
- `AGENTS.md` (agents.md standard) and portable Claude Code setup; skills in the
  Agent Skills (agentskills.io) format; an executable agent layer (skills + subagents).
- Data-engineering layer; configurable scoring governance; connector and
  agent-orchestration contracts; event-research pilot profile; browser research
  method comparison; demo vault + external-import staging; HubSpot writeback governance.
- Research-workflow and governance docs, architecture docs with Mermaid diagrams,
  and health checks.

[Unreleased]: https://example.invalid/saleswiki/compare/v0.4.0...HEAD
[0.4.0]: https://example.invalid/saleswiki/releases/tag/v0.4.0
[0.3.0]: https://example.invalid/saleswiki/releases/tag/v0.3.0
[0.2.0]: https://example.invalid/saleswiki/releases/tag/v0.2.0
[0.1.0]: https://example.invalid/saleswiki/releases/tag/v0.1.0
