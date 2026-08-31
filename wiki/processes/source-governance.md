# Source Governance

Source governance defines what can be collected, how reliable it is and how it may be used.

## Source Classes

- `primary` - company site, event organizer, filing, transcript, CRM.
- `trusted-news` - reputable news/industry source.
- `industry-media` - niche media/blog with useful coverage.
- `database` - Apollo, Crunchbase or similar.
- `social-public` - public posts/profiles when allowed and relevant.
- `syndicated` - republished press releases or duplicated articles.
- `unknown` - unverified source.

## Reliability Scores

- `high` - primary or consistently reliable.
- `medium` - useful but may need confirmation.
- `low` - noisy, biased, unclear or requires strong corroboration.

## Usage Rules

- Primary sources can establish facts.
- Trusted independent sources can corroborate facts.
- Syndicated copies show reach but weak independence.
- Low-reliability sources should not drive action without confirmation.
- Social/public data should be used carefully and only when relevant.

## Access And Licensing

For each managed source, track:

- source access type: `free`, `paid`, `restricted`, `licensed`, `internal-system`
- access label: `public`, `internal`, `sales-confidential`, `personal-data`, `legal-review`
- collection method
- usage limitations
- citation requirement
- owner
- review cadence

## LinkedIn And Social Sources

Use only allowed, relevant public information. Do not over-automate or create tooling that violates platform or company policy.

Record:

- what was checked
- why it was relevant
- source URL/reference
- confidence
- whether it can be used in outreach

## Agent Behavior

Agents should:

1. Prefer primary sources for factual claims.
2. Use independent sources for corroboration.
3. Mark low-quality sources as low confidence.
4. Track rejected/noisy sources.
5. Respect access/licensing restrictions.
6. Avoid creating action recommendations from weak sources alone.
