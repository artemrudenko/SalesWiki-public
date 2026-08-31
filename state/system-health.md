# System Health

Last verified: 2026-08-20

## Executive Status

| Area | Status | Evidence / limitation |
| --- | --- | --- |
| Product validation | **Not started** | No real entity cards or completed real-data pilot; [[permissioned-knowledge-pilot-runbook]] is ready. |
| Production knowledge | **Built-empty** | Templates, processes, dashboards and index builders exist; production `wiki/entities/` contains no real cards. |
| Permissioned core | **Implemented and verified locally** | 17 MCP tools, role-aware extract-only answers, RBAC+ABAC, signed approvals, single-writer worker, rollback and audit chain. |
| Identity | **Demo fixture only** | Shared per-request identity/SSO remains future work; fixture identity is blocked from non-demo vaults unless an operator explicitly accepts the pilot override. |
| Data inflow | **Manual / staged only** | HubSpot and Drive/Meet are contract definitions, not live connectors; web research is manual-first. |
| Writeback | **Proposal-only** | Governed card proposals work; no autonomous HubSpot writeback is enabled. |
| Personal data | **Handles-only design** | ADR-0018 forbids personal-data bodies in git; the external erasable store is not implemented. |
| Public release | **Ready after cleanup** | MIT license, security/contribution docs, release-review scanner, Docker/local deployment docs and sanitized examples are present. |
| Operations | **Partial** | CI, health check, public-release review, local tests, Docker checks and demo smoke exist; rate limits, admin status, backup/restore drill and hosted incident controls remain. |
| Demo | **Ready** | Standard demo vault and permissioned role-contrast/governance demo are synthetic and isolated from production. |

## Current Counts

- Companies: 0
- People: 0
- Articles: 0
- Leads: 0
- Deals: 0
- Calls: 0
- News items: 0
- Events: 0
- Managed news sources: 5 starter sources
- Real pilot data: 0 cards / 0 event source-note files / 0 staged event pilot reports
- Derived index rows: 0 production rows; synthetic fixture build validates non-empty output separately
- Dashboard snapshot rows: 0 production rows because there are no real cards yet
- Standard demo entity rows: 39 synthetic cards
- Permissioned demo rows: 77 synthetic cards/refs across broad, sales-confidential and personal-data boundaries
- Scoring config models: 4 active models (`inbound-lead`, `outbound-lead`, `qualification-mql`, `deal`)
- Connector contracts: 4 configured connector families (`hubspot`, `google-drive-meet`, `slack-or-email-digest`, `web-research`)
- Event research profiles: 1 active supervised profile (`b2b-conference-sales-marketing`)
- Agent routes: 7 configured request intents
- Gateway tools: 17
- Automated tests: 486 passing in the MCP-enabled environment
- Public-release guardrails: `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `docs/DEPLOYMENT.en.md`, `scripts/public_release_review.py`

## Immediate Priorities

1. Run the four-week `lead_priority` pilot from [[permissioned-knowledge-pilot-runbook]] with 10–20 real leads in an out-of-repo pilot vault.
2. Use one controlled HubSpot CSV export as the pilot inflow; do not expand connector scope before the value hypothesis is measured.
3. Keep real contacts and transcripts as references/handles until an erasable personal-data store exists.
4. If the pilot passes, implement one read-only HubSpot inflow and choose the shared identity/deployment path.
5. Only then expand card types, automated monitoring, writeback or additional user interfaces.

## Verification

Verified on 2026-08-20:

```bash
python3 scripts/public_release_review.py
python3 scripts/health_check.py
python3 -m unittest discover -s tests
.venv/bin/python -m unittest discover -s tests
python3 scripts/demo_dryrun.py --quiet
docker compose config
docker compose run --build --rm check
docker compose run --build --rm health
docker compose run --build --rm test
docker compose run --rm demo
```

- Public release review: `Errors: 0`, `Warnings: 0`
- Health check: `Errors: 0`, `Warnings: 0`
- Standard-library suite: 486 passing, 2 skipped MCP-dependent checks
- MCP-enabled suite: 486 passing
- Demo dry run: all checks passed
- Docker checks: public-release review, health check, full test suite and demo smoke passed

## Canonical Follow-Ups

- [[permissioned-knowledge-pilot-runbook]] — next product-validation step
- [[ROADMAP.en]] — remaining validation, identity, connector and operations work
- [[DEPLOYMENT.en]] — local and Docker deployment path for the public starter kit
- [[permissioned-knowledge-sso-design]] — gates for real shared identity
- [[buy-vs-build]] — investment decision boundaries
