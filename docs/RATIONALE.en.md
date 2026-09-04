# SalesWiki Rationale

SalesWiki began as a research question: **can a plain, portable wiki become a
useful brain for sales and marketing without turning into either an ungoverned
folder or an opaque AI search box?**

Sales teams gave us a demanding place to test the idea. Their evidence is spread
across CRM notes, call transcripts, research, private cases and spreadsheets.
The same context must support daily decisions, but it has different owners,
freshness windows and access levels. A fluent answer is not enough: the user
needs to know where it came from, whether it is stale and what to do next.

The wiki model is the product hypothesis underneath those answers. One linked
set of company, person, deal, call, campaign and source cards holds the team's
current shared understanding. Raw evidence stays immutable. Card history,
proposals and review records preserve how that understanding changed. Policy
then produces different permitted views for sales, marketing and other roles.

We are not claiming that "wiki brain" is a proven product category. SalesWiki is
a public reference implementation and an experiment that makes its hypothesis
inspectable. The synthetic demo proves the mechanics. A private pilot must still
prove that the workflow is better than the team's current tools.

The project is intentionally a public reference implementation, not a hosted
SaaS. Its useful idea is the operating model:

1. keep durable knowledge in a plain Markdown/Obsidian vault;
2. keep raw evidence immutable and linked;
3. answer from cited fields and sections, not generated guesses;
4. enforce role boundaries before retrieval;
5. route sensitive changes through proposal, review and a single-writer worker.

## What We Are Trying To Learn

- Can typed Markdown be a small, understandable data plane for GTM knowledge?
- Do cited, extract-only answers earn more trust than plausible summaries?
- Can agents maintain a wiki without silently rewriting protected facts?
- Does separating raw evidence, compiled cards and derived views reduce drift?
- Is governed correction valuable enough to justify more machinery than search?
- Which part should remain human-curated, and which part can be automated safely?

This explains why the repository includes contracts, freshness rules, audit
traces and synthetic failure paths before it includes many live connectors. We
are testing the knowledge operating model first. Infrastructure should follow
evidence from use, not substitute for it.

## Who This Is For

Good fit:

- small B2B sales or founder-led GTM teams;
- RevOps / sales ops people who already curate knowledge manually;
- agencies or consultants managing repeated sales/account context;
- teams that care about portability, auditability and explicit data boundaries.

Poor fit:

- teams that need a polished CRM replacement;
- teams with no technical owner;
- teams already satisfied with Notion/Glean/HubSpot search and enrichment;
- enterprise deployments that need production SSO, hosted operations and
  connector governance immediately.

## Why Not Just Buy?

Buying is the default for most teams. SalesWiki is worth building on only when
three requirements matter together:

- deterministic, extract-only answers with mandatory citations;
- governed change control rather than ordinary page editing;
- an owned, portable Markdown/JSON data plane.

If the job is only "search our docs with AI", use an existing product. The
buy-vs-build rationale is in `docs/engineering/buy-vs-build.md`.

## Benefits And Costs

| Choice | Benefit | Cost |
| --- | --- | --- |
| Markdown as source of truth | readable, diffable, portable and easy to back up | weaker transactions and queries than a database |
| Explicit card contracts | predictable extraction and visible schema drift | templates and migrations need maintenance |
| Extract-only answers | honest missing data and traceable claims | less fluent and less flexible than open-ended generation |
| Authorization before retrieval | closed content never enters answer assembly | identity and boundary design must be correct up front |
| Proposal → approval → worker | reviewable, reversible sensitive changes | more steps than ordinary page editing |
| Generated indexes and dashboards | fast views without making them authoritative | derived files must be rebuilt and checked |
| Owned data and policy plane | portability and control over semantics | the operator owns backups, retention, connectors and incidents |

The approach works best when those benefits solve an actual operating constraint.
For a team that only wants document search, the costs are unnecessary.

## What Is Included

- Obsidian-compatible vault structure and templates.
- Health checks, generated indexes and dashboard snapshots.
- Synthetic demo data.
- Permissioned MCP gateway with role-aware read/propose/govern tools.
- Single-writer worker for approved changes.
- Docker and local checks for a repeatable public preview.

## What Is Not Included Yet

- production multi-user SSO;
- live HubSpot/Drive/Meet connectors;
- hosted backup/restore and incident response;
- external erasable personal-data store;
- managed UI beyond Obsidian, MCP clients and the optional Rocket.Chat demo.

The roadmap is intentionally narrow: validate the workflow on real data before
adding more connectors or interfaces.

## Recommendations For Builders

1. Start with one repeated decision, such as "which lead needs action today?"
   Do not model the whole company before a user prefers one real answer.
2. Keep public platform code, synthetic demo data and private pilot data in
   physically separate contours.
3. Define identity and access boundaries before ingesting transcripts or contacts.
4. Make missing and stale evidence visible; do not optimize only for answer fluency.
5. Keep writes behind a proposal and a single controlled writer until the team has
   evidence that a narrower path is safe.
6. Measure answer usefulness, correction frequency and curator time. These reveal
   whether the wiki brain is helping or merely moving maintenance elsewhere.
7. Add vector search, live connectors and richer interfaces only when a validated
   workflow needs them.

The experiment succeeds even if a pilot tells a team to buy instead. The point is
to make that decision with evidence and a clear understanding of the trade-offs.
