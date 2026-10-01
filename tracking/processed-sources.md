# Processed Sources

Use this ledger for every reviewed URL, file, article, event page, transcript,
search result or note.

## Fields

| Field | Meaning |
| --- | --- |
| `source_id` | Stable ID, usually date plus normalized domain/title hash. |
| `canonical_url_or_path` | Canonical URL or raw file path. |
| `normalized_title` | Clean title without tracking noise. |
| `source_type` | `news | event-page | company-page | article | post | transcript | crm | note | search-result`. |
| `entities` | Companies, people, events, deals or topics. |
| `first_seen` | First collection date. |
| `last_checked` | Most recent review date. |
| `status` | `accepted | rejected | duplicate | superseded | queued | needs-review`. |
| `duplicate_of` | Source ID or URL if duplicate. |
| `corroborates` | Claim IDs or wiki pages this supports. |
| `output_pages` | Wiki pages created or updated. |
| `notes` | Short decision reason. |

## Ledger

| source_id | canonical_url_or_path | normalized_title | source_type | entities | first_seen | last_checked | status | duplicate_of | corroborates | output_pages | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| src-20261001-govuk-data-quality-framework | https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework-guidance | The Government Data Quality Framework: guidance | article | [[Freshness And Decay]] | 2026-10-01 | 2026-10-01 | accepted |  | [[Freshness And Decay]] | [[data-quality-review-loop-2026-10-01]]; [[permissioned-knowledge-pilot-runbook]]; [[devto-04-safe-private-pilot]] | Metadata-only review; use-specific quality, log findings over time, investigate cause and fix near source. |
| src-20261001-govuk-data-quality-issues | https://www.gov.uk/government/publications/implement-a-data-quality-action-plan/data-quality-issues-framework | Data Quality Issues Framework | article | [[Freshness And Decay]] | 2026-10-01 | 2026-10-01 | accepted |  | [[Freshness And Decay]] | [[data-quality-review-loop-2026-10-01]]; [[permissioned-knowledge-pilot-runbook]]; [[devto-04-safe-private-pilot]] | Metadata-only review; response should account for issue impact and priority. |
| src-20261001-hubspot-data-quality-tools | https://knowledge.hubspot.com/data-management/use-data-quality-tools | Use data quality tools | article | [[Freshness And Decay]] | 2026-10-01 | 2026-10-01 | accepted |  | [[Freshness And Decay]] | [[data-quality-review-loop-2026-10-01]]; [[devto-05-vendor-first-integrations]] | Metadata-only review of official CRM product docs; illustrates ongoing issue review, scoped access and weekly digest. |
| src-20261001-revopscoop-data-quality | https://www.revopscoop.com/webinar-series/dirty-crm-data-ai-readiness | From Dirty CRM Data to Trusted Account Intelligence: A RevOps Playbook for AI Readiness | article | [[Freshness And Decay]] | 2026-10-01 | 2026-10-01 | accepted |  | [[Freshness And Decay]] | [[data-quality-review-loop-2026-10-01]]; [[devto-05-vendor-first-integrations]] | Practitioner discussion; do not present as universal consensus or benchmark. |
| src-oer-uark-intro-marketing-2022 | https://uark.pressbooks.pub/intromarketinguark/ | Introduction to Marketing - MKTG 34303 | file-import | [[Method Library - Sales and Marketing]] | 2026-09-17 | 2026-09-17 | accepted |  | [[Call Prep - Evidence-First Completeness Lens]]; [[Campaign Brief - Evidence-First Completeness Lens]] | [[Source - Introduction to Marketing - MKTG 34303]]; [[method-library-intake]] | CC BY 4.0 publisher edition; remote-reference manifest only because separately licensed media is excluded. |
| src-oer-bccampus-digital-marketing-2023 | https://collection.bccampus.ca/textbook/j6x4E87p/ | Foundations in Digital Marketing | file-import | [[Method Library - Sales and Marketing]] | 2026-09-17 | 2026-09-17 | accepted |  | [[Campaign Brief - Evidence-First Completeness Lens]] | [[Source - Foundations in Digital Marketing]]; [[method-library-intake]] | CC BY 4.0 publisher edition; remote-reference manifest only because individual media and linked materials can have separate terms. |
