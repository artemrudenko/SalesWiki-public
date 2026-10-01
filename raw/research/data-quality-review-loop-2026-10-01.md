# Data-quality review loop — source notes

Collected and reviewed: 2026-10-01

This is a metadata-only research note. The linked pages remain the source of
truth; their full text has not been copied into the repository. The sources
inform a proposed stale-review process, not facts about any customer or proof
that SalesWiki already diagnoses data problems.

## Sources reviewed

| Source | Relevant guidance | How it informs this work | Limit |
| --- | --- | --- | --- |
| [The Government Data Quality Framework: guidance](https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework-guidance) | Define quality against user need; log findings over time; investigate systemic and one-off causes; act near the source; repeat measurements. | Separate stale detection from root-cause analysis; keep timestamps, outcomes and confirmed/unknown causes. | General data-management guidance, not a SalesWiki implementation evaluation. |
| [Data Quality Issues Framework](https://www.gov.uk/government/publications/implement-a-data-quality-action-plan/data-quality-issues-framework) | Assess impact and urgency when choosing what to fix. | Do not let age alone decide whether an account is low priority; measure potential decision impact. | General framework, not a CRM-specific product design. |
| [HubSpot: Use data quality tools](https://knowledge.hubspot.com/data-management/use-data-quality-tools) | Data issue summaries, recommended actions, property insights, monitoring and weekly digests. | An example of CRM quality work as ongoing review with scoped access and actionable issue views. | Product documentation describes HubSpot features; it is not a recommendation to adopt HubSpot tools. |
| [RevOps Co-op: Dirty CRM Data to Trusted Account Intelligence](https://www.revopscoop.com/webinar-series/dirty-crm-data-ai-readiness) | Practitioner discussion says CRM data decays, broad enrichment can create maintenance debt, and useful coverage should connect to an action. | Keep the review process tied to decisions and avoid tracking completeness for its own sake. | Practitioner discussion, not an independently validated benchmark or universal consensus. |

## Applied artifacts

- `wiki/processes/freshness-and-decay.md` — canonical review guidance.
- `docs/engineering/permissioned-knowledge-pilot-runbook.md` — pilot event fields and weekly review.
- `docs/engineering/permissioned-knowledge-architecture.md` — separate quality-event purpose and least-privilege views.
- `docs/adr/0035-quality-review-telemetry-and-access.md` — proposed decision; no runtime quality-event stream or new role is implemented yet.
- `docs/publications/devto-03-one-decision-pilot.md`, `devto-04-safe-private-pilot.md`, `devto-05-vendor-first-integrations.md` — public draft explanations and direct source links.

## Decision

Accepted as design input for the pilot and public drafts. Capture review timing,
outcome, decision impact and cause confidence separately from access audit.
Record `unknown` when the evidence does not establish a cause. Reassess whether
a structured runtime stream or independent audit capability is justified only
after pilot evidence.
