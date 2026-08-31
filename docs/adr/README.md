# Architecture Decision Records (ADRs)

This directory records the **why** behind SalesWiki's significant decisions —
the context, the choice, its consequences and the alternatives that were
rejected. Other docs describe *what* the system is and *how* to use it; ADRs
explain *why* it is that way, so a decision can be understood, revisited or
superseded later instead of silently drifting.

ADRs span both the wiki-brain **product** model and the **engineering** of the
permissioned-knowledge service, which is why they live at `docs/adr/` rather than
under `docs/engineering/` or `wiki/processes/`.

## Format and process

- One decision per file, named `NNNN-kebab-title.md`, copied from
  [`0000-template.md`](0000-template.md).
- Sections: **Status · Context · Decision · Consequences · Alternatives
  considered · References**. Frontmatter: `status`, `date`, `deciders`.
- **Status** lifecycle: `Proposed` → `Accepted` → `Superseded by ADR-NNNN` /
  `Deprecated`. Never delete or rewrite an accepted ADR — supersede it with a new
  one and update the old one's Status line to point forward.
- **When to write one:** any architectural or cross-cutting decision — a new
  boundary, a change to the authorization model, a schema/contract change, a new
  card type, an identity/deployment choice. Link the new ADR from the doc it
  affects.
- ADRs 0001–0016 were **backfilled** on 2026-06-24 from decisions already
  established across `AGENTS.md`, `README.md`, `wiki/processes/` and
  `docs/engineering/`; their Context notes where each was originally made.

## Index

### Product & vault model
- [ADR-0001](0001-obsidian-first-markdown-vault.md) — Obsidian-first Markdown vault as the source of truth — Markdown vault over a database; human-readable, git-versioned, no server dependency.
- [ADR-0002](0002-raw-evidence-is-immutable.md) — Raw evidence is immutable; corrections appended, never rewritten — keep `raw/` sources verbatim; add correction notes, never edit or delete.
- [ADR-0003](0003-controlled-profile-vs-live-intelligence.md) — Separate Controlled Profile from Live Intelligence (`profile_lock`) — protect core identity fields; route changes through Review Needed.
- [ADR-0004](0004-hubspot-remains-crm-source-of-truth.md) — HubSpot remains the CRM source of truth — SalesWiki stages approvable writeback proposals; never auto-overwrites curated CRM data.

### Data model & configuration
- [ADR-0005](0005-typed-cards-and-health-check-linter.md) — Typed entity cards with required sections — fixed card shape gated by `health_check.py` as a failing test.
- [ADR-0006](0006-configuration-first-machine-readable-contracts.md) — Configuration-first: schemas as machine-readable contracts — JSON schemas are the source of truth; docs explain, the linter validates.
- [ADR-0007](0007-opaque-ulid-identifiers-via-chokepoint.md) — Opaque typed ULID identifiers via a single chokepoint — rename-safe `<type>_<ULID>`, minted once, deduped, ledgered.
- [ADR-0008](0008-demo-and-pilot-data-isolation.md) — Demo vault separated from production; pilot data outside the repo — three contours, boundary failures enforced by `health_check`.

### Permissioned-knowledge core
- [ADR-0009](0009-boundary-by-physical-location-fail-closed.md) — Permission boundary is physical location, not a YAML label; fail-closed default — unmatched paths quarantine, never leak.
- [ADR-0010](0010-rbac-plus-abac-authorization.md) — RBAC + ABAC authorization model — roles set boundaries; attributes narrow sales-confidential by ownership/team.
- [ADR-0011](0011-read-propose-gateway-single-writer-worker.md) — Read/propose-only gateway separated from a single-writer worker — gateway never writes; one locked writer applies approved proposals transactionally.
- [ADR-0012](0012-answer-contract-extract-only.md) — Answer Contract: extract-only, never generate, mandatory citations — cited card values only, honest `not-found`, no hallucination.

### Identity, delivery & operations
- [ADR-0013](0013-mvp-fixture-identity-sso-later.md) — MVP identity via a fixture provider; SSO/OIDC deferred — role resolved server-side; OIDC slots in later behind the same Protocol.
- [ADR-0014](0014-docker-deferred-for-mvp.md) — superseded historical decision: Docker packaging deferred for the local MVP.
- [ADR-0015](0015-append-only-tamper-evident-audit-chain.md) — Append-only, tamper-evident audit hash-chain — SHA-256 prev/hash chain + single-lock read-modify-append with flush/fsync (race-safe).
- [ADR-0016](0016-chat-bridge-role-self-asserted-demo-only.md) — Rocket.Chat bridge role is self-asserted (demo only) — chat command picks the role over the real core; production resolves role from SSO.
- [ADR-0017](0017-llm-client-side-labeled-layer.md) — LLM is a labeled client-side layer — the gateway never generates; a key is needed only where our own code calls a model (headless chat bridge), never for MCP clients.
- [ADR-0018](0018-personal-data-erasure-vs-git-history.md) — personal-data erasure vs git history — PII bodies never enter a git-tracked vault (handles only, external erasable store); resolves the right-to-erasure vs immutable-history tension before real PII lands.
- [ADR-0019](0019-public-preview-and-docker-starter-path.md) — public preview ships with a Docker starter path, not production hosting.
- [ADR-0020](0020-vendor-first-mcp-and-channel-adapters.md) — prefer official vendor MCP/native client paths before custom connectors or chat bots; writes remain governed.
- [ADR-0021](0021-layout-neutral-mcp-graph-read-model.md) — use a versioned, layout-neutral MCP graph read model; policy stays server-side and the client owns rendering positions.
- [ADR-0022](0022-demo-workbench-bff-over-mcp-stdio.md) — connect the local Workbench through a narrow demo-only BFF that invokes the real MCP stdio tool; fixed fixture identity remains synthetic-only.
- [ADR-0023](0023-review-first-workbench-import.md) — turn small pasted CSVs and meeting notes into visible drafts, then a bounded review proposal; raw text never crosses the demo BFF.
- [ADR-0024](0024-workbench-review-actions-through-bff.md) — expose review decisions through a server-owned, allowlisted BFF; browser actions remain proposal-state changes, never card writes.
- [ADR-0025](0025-demo-persona-switching-is-server-session-bound.md) — demo persona switching is bound to an opaque server session; the browser never asserts a role.
- [ADR-0026](0026-workbench-review-capability-hint.md) — Workbench review navigation is exposed only through a server-owned reviewer capability; contributors never receive the shared queue.
- [ADR-0027](0027-role-aware-company-search.md) — Workbench company search is a deterministic, server-authorized resolver; hidden accounts are omitted before results reach the browser.
- [ADR-0028](0028-policy-filtered-dashboard-observations.md) — policy-filtered dashboard read model with dated observations.
- [ADR-0029](0029-guided-assistant-before-freeform-llm.md) — guided, cited assistant before free-form LLM chat.
- [ADR-0030](0030-history-free-public-release-snapshots.md) — export a checked, history-free public repository snapshot from the private source repository.
- [ADR-0031](0031-signed-audit-checkpoints.md) — signed audit checkpoints outside the runtime volume — protect a verified log prefix from clean tail deletion without overstating the guarantee as immutable storage.
