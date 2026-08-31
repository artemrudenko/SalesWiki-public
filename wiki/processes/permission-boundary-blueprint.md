# Permission Boundary Blueprint

SalesWiki uses `access` labels for classification, but labels are not enforcement. Before real CRM exports, call transcripts or personal data enter the system, the team must choose and operate physical permission boundaries. This page owns the **physical** boundary model and the pre-ingest gate; labels, roles, the role-access matrix and redaction/sanitization rules live in [[access-and-redaction-policy]].

## Boundary Model

| Boundary | Intended contents | Typical access |
| --- | --- | --- |
| Broad vault | sanitized summaries, public/internal market intelligence, approved assets | sales, marketing, leadership |
| Sales-confidential area | leads, deals, account plans, pricing, negotiation, private sales context | sales, HoS, RevOps, selected curators |
| Personal-data storage | raw transcripts, recordings, email/contact exports, identifiable personal data | minimal approved operators only |
| Legal-review queue | customer claims, sensitive private cases, export/publication candidates | reviewer/legal/curator |

## Minimum Controls Before Sensitive Ingest

Do not ingest real transcripts, recordings, email exports or CRM contact exports until:

1. The storage location is mapped to one boundary above.
2. The default `access` label is known.
3. The allowed readers are documented.
4. The redaction path to a broad summary is documented.
5. The approval owner for downgrading access is named.
6. `state/access-review.md` is used for exceptions, exports and downgrades.

## Default Placement

- Company and topic summaries: broad vault unless they contain sensitive CRM/deal/call details.
- Lead, deal, account plan and enrichment cards: sales-confidential.
- Call cards: sales-confidential by default; raw transcript/recording references are personal-data when identifiable personal data is present.
- Private cases: sales-confidential until sanitized or legal-reviewed.
- Public source cards: broad vault, with `source_access_type` capturing licensing/access restrictions.

## Operating Rule

When unsure, use the more restrictive boundary and create a sanitized summary for broad access.
