# SalesWiki Public Preview Roadmap

This roadmap is intentionally small. The project should not expand horizontally
until the core workflow proves useful on real sales work.

## Current State

SalesWiki is ready as a public reference implementation / starter kit:

- synthetic demo vault works;
- local and Docker checks pass;
- role-aware MCP tools are implemented;
- answers are cited and extract-only;
- proposal / approval / worker flow is implemented;
- real customer data is intentionally absent from the repository.

## Near-Term Work

1. **Run a real-data pilot outside this repo.**
   Use `docs/engineering/permissioned-knowledge-pilot-runbook.md` with 10–20
   real leads in a private vault.

2. **Validate one workflow.**
   Start with `lead_priority`: “which leads should I touch today and why?”

3. **Validate the controlled CSV/note intake in a pilot.**
   The demo previews small pasted CSVs or meeting notes and sends only a
   reviewed summary into the proposal queue. Validate this before a live API
   connector or bulk importer.

4. **Choose production identity only after value is proven.**
   The current fixture identity is demo-only. A shared runtime needs
   per-request SSO before real multi-user access.

5. **Keep personal data out of git.**
   Use opaque handles until an external erasable store exists.

6. **Build the integration foundation without adding connector breadth.**
   Follow `docs/engineering/integration-platform-plan.md`: typed configuration,
   transport-neutral chat, Rocket.Chat migration and remote MCP readiness.

7. **Use vendor-first integration gates.**
   Evaluate official HubSpot MCP for the first read-only CRM pilot after the
   `lead_priority` value gate. Prefer Slackbot and Microsoft 365 native MCP-client
   paths before custom Slack or Teams bots.

## Later Work

- **Daily Workbench for small B2B teams (complete).** A role-aware “Today for
  me” queue built from `my_day`: a small set of next actions with a human
  explanation, source-aware account drill-down, and no new scoring model.
- **Explainable account temperature (complete).** Hot / warm / cold / at-risk
  labels derived only from role-visible evidence; every label shows its rule.
- **Polish B2B starter mode (starter slice complete).** Polish-language guided
  onboarding is available in the demo; durable Polish templates and import are
  still validation work with 2–30 person relationship-led teams.
- **Controlled Workbench import (starter slice complete).** A small pasted CSV
  or meeting note becomes local, reviewable drafts for the open account; only a
  bounded summary enters the governed proposal queue. Bulk files and automatic
  card creation remain deliberately out of scope.
- **Workbench review inbox (starter slice complete).** A curator can inspect
  scoped proposals, open the linked account and record an approve/send-back
  decision. The BFF keeps identity and action allowlisting server-side; a
  separate worker remains responsible for applying approval later.
- **Worker publication lifecycle (pilot gate).** Before a real-data pilot, an
  applied proposal must validate the full vault and refresh derived indexes and
  dashboard snapshots in the private deployment workflow. Automatic Git commits
  remain intentionally out of the worker: repository publication needs an
  explicit human decision.
- **Governed account monitoring (configuration slice complete).** Opt-in signal
  categories and cadence can be configured locally; source-cited collection and
  an action inbox remain gated on connector and pilot validation.
- production SSO / identity broker;
- read-only HubSpot connector;
- Drive/Meet ingest with explicit approvals;
- backup/restore and incident drills;
- hosted rate limits and admin status;
- optional lightweight web UI;
- packaged examples for more GTM use cases.
- demand-driven Telegram or other chat adapters after the common runtime is proven.

## Non-Goals For Now

- becoming a CRM;
- replacing HubSpot;
- autonomous writeback to third-party systems;
- broad event scraping automation before a real sales use case asks for it;
- generic enterprise search.
