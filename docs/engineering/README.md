# Engineering And Architecture Docs

This folder holds **engineering documentation about the software itself** — the
permissioned MCP knowledge service (`saleswiki_mcp/`), its architecture, demo
walkthroughs and extension designs.

## Why this is separate from `wiki/processes/`

SalesWiki is an Obsidian-first wiki-brain. The two doc layers serve different readers:

- `wiki/processes/` — the **sales/marketing operating model**: how agents maintain the vault (card taxonomy, ingest, scoring, monitoring, governance, freshness, access/redaction). Read for daily knowledge work. Per `wiki/README.md`, the wiki layer is "written for daily use by marketing and sales employees".
- `docs/engineering/` — **how the code works**: architecture, field-extraction
  contracts, SSO design, optional chat bridge behavior and demo walkthroughs.
  Read by engineers extending or operating the service, not by sales/marketing
  users.

Both still open inside the Obsidian vault, so `[[wikilinks]]` to these files keep resolving and they remain in the graph.

The **why** behind decisions (the rationale, consequences and rejected alternatives, including the engineering ones referenced here) lives in Architecture Decision Records under [`docs/adr/`](../adr/README.md).

## Placement rule (where new docs go)

When you add a doc, ask: **does it describe the sales/marketing operating model, or the software/code?**

- Operating model, vault conventions, research/governance workflow → `wiki/processes/`.
- Software architecture, code-coupling contract, deployment/runtime design,
  identity design and system demo → `docs/engineering/`.

Anything about building, testing, securing or deploying the permissioned MCP service (or future services) belongs here.

## Current contents

- `code-structure.md` — dependency direction, runtime module ownership and
  extension rules used to prevent new god modules.
- `integration-platform-plan.md` — executable plan for typed runtime
  configuration, transport-neutral chat, remote MCP and vendor-first connectors.
- `mcp-graph-adapter.md` — versioned GraphView contract and rollout plan for the
  data-driven Knowledge Workbench.
- `workbench-dashboard-v1.md` — decision-signal widgets, their synthetic-demo
  provenance and the role-aware production read-model path.
- `self-contained-demo-foundation.md` — policy-filtered dashboard, synthetic
  history, mock adapters and safe local input without an external connection.
- `workbench-review-inbox.md` — the governed proposal inbox and its synthetic
  demo persona-session boundary.
- `permissioned-knowledge-overview.md` — single visual entry point and doc map for the permissioned-knowledge system.
- `permissioned-knowledge-architecture.md` — current, maintained architecture (multi-vault, MCP, RBAC+ABAC, approval, security, UX).
- `permissioned-knowledge-sso-design.md` — future per-request SSO/OIDC identity design for a shared runtime.
- `buy-vs-build.md` — honest buy-vs-build comparison (Notion/Guru/Glean/Claude+connectors/HubSpot AI vs building): when the permissioned build is justified and when to buy instead.
- `llm-usage-architecture.md` — where LLMs run and when an API key is needed: generative steps live in the labeled client layer; the core/gateway/worker never generate (ADR-0017).
- `permissioned-knowledge-field-extraction.md` — declarative card-shape decoupling profile (`schemas/field-extraction.json`).
- `permissioned-knowledge-access-requests.md` — design + scope of the governed `request_access` → approve → scoped-grant → revoke loop (surfaced in the Rocket.Chat bridge).
- `permissioned-knowledge-demo.md` — end-to-end demo walkthrough.
- `permissioned-knowledge-demo-runbook.md` — step-by-step runbook for presenting the demo.
- `permissioned-knowledge-pilot-runbook.md` — four-week single-operator pilot of the `lead_priority` wedge on real data (seeding, inflow, staleness measure, go/no-go).

Public product context lives one level up:

- `../RATIONALE.en.md` — why this project exists and who it fits.
- `../ROADMAP.en.md` — current public-preview roadmap and non-goals.
- `../DEPLOYMENT.en.md` — local and Docker deployment path.
- `../REPOSITORY_CONTENTS.en.md` — exact public/private repository boundary.
