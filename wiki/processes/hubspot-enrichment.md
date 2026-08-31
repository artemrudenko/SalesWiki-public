# HubSpot Enrichment

HubSpot is the operational CRM source of truth. SalesWiki should enrich and explain CRM data, not silently overwrite it.

## Preferred Sources

- HubSpot for CRM objects, owners, stages and activity.
- Apollo.io for person/company enrichment.
- Company website for primary company facts.
- Open web for public validation.
- Crunchbase when available for company/funding context.

Avoid Clay dependency unless explicitly approved later.

## Enrichment Workflow

1. Identify target object: company, contact, lead or deal.
2. Read current HubSpot fields.
3. Create an enrichment record.
4. Check Apollo.io, company site and optional Crunchbase/open web.
5. Compare enriched data to existing CRM fields.
6. Propose CRM updates with confidence.
7. Flag conflicts, duplicates and low-confidence data.
8. Update wiki cards with sourced context.
9. CRM writeback requires approval or a defined sync rule.

## HubSpot Card Fill

SalesWiki may prepare values for HubSpot cards, but the default state is a staged proposal.

Allowed fill targets and their field modes are canonical in `wiki/processes/hubspot-field-matrix.md`; consult it before proposing any fill.

Good first fields:

- `AI summary` on Company / Contact
- `AI score` on Company / Contact
- `AI risk summary` on Deal
- `AI deal score` on Deal
- `Next activity` or Task is `approved-writeback` in the field matrix (not a free first fill); only when the SalesWiki task workflow already has owner, due date and reason, and the writeback is approved

Before execution, every fill needs:

- existing `hubspot_id`
- current/previous HubSpot value
- source and confidence
- field-matrix mode
- approver or system-writeback rule
- proposal entry in `state/hubspot-writeback-proposals.md`

If a field does not exist in HubSpot yet, create a RevOps setup task/proposal first. Do not simulate the field in free-text notes unless the owner approves that fallback.

## Do Not Silently Overwrite

Do not automatically overwrite:

- owner
- lifecycle stage
- deal stage
- email
- phone
- company domain
- personal data
- manually curated notes

Propose changes in the enrichment record instead.
