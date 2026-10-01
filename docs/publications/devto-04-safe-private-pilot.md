---
title: "What must change before a sales demo uses real data? — SalesWiki, Part 4 of 5"
published: false
description: Run the synthetic demo, see where customer data belongs, and decide what a small private pilot would need to prove.
tags: opensource, mcp, ai, privacy
series: Building SalesWiki in the open
cover_image: https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/mmxfn3ru1kkbg47owtp3.png
---

The public demo uses invented accounts. You can follow an answer to its sources and see how a correction enters review. But what changes when a team wants to try the same workflow with a real customer record?

That question matters more than whether the demo looks convincing. In [Part 3](https://dev.to/artemr_rudenko_0bf2c2c505/what-should-a-sales-knowledge-base-help-someone-decide-saleswiki-part-3-of-5-pb0), I chose one repeated decision to test: which account needs attention today, and why? Here I show how to run the synthetic demo, where real data must go, and what a private pilot would need to prove. None of this establishes that the workflow already helps a real team.

The boundary is simple: the public repository holds the platform, its demo holds synthetic cards, and real customer data belongs in a separate private vault.

| Contour | Location | Data rule |
| --- | --- | --- |
| Platform | Public SalesWiki repository | Code, schemas, templates and docs |
| Demo | `demo/` inside the repository | Synthetic cards only |
| Pilot | A separate private vault outside the repository | Real accounts, deals, contacts and transcripts |

The public preview supports a local demo or single-operator pilot and Docker-based checks. It is not a hosted multi-user service yet.

## Pick the shortest path first

If you want to understand the interaction before installing anything, take the
guided Workbench tour. If you want to inspect the cards and controls, run the
local demo. If you want to test whether the workflow helps a real team, first
define the repeated decision in Part 3, then use the private-pilot section.
These are different questions, so they should not become one large setup
exercise.

## What you need

Required:

- Git
- Python 3.11 or newer
- a POSIX-like shell

Recommended:

- Obsidian for cards, links, graph view and `.base` dashboards
- Docker with Compose V2 for repeatable isolated checks
- an MCP client such as Claude Desktop, Claude Code or Cowork

Node.js is optional. The core vault checks use the Python standard library. The
MCP gateway needs the dependency listed in `requirements.txt`.

## Run the first demo

```bash
git clone https://github.com/artemrudenko/SalesWiki-public.git SalesWiki
cd SalesWiki
python3 scripts/first_run.py
```

The command does five jobs:

1. Creates `.venv`.
2. Installs the MCP SDK dependency.
3. Runs the public release review.
4. Runs the vault health check.
5. Runs the permissioned demo smoke test.

A clean run ends with output like this:

```text
SalesWiki public release review
Errors: 0
Warnings: 0
SalesWiki health check
Errors: 0
Warnings: 0
DEMO DRY RUN: ALL CHECKS PASSED
SalesWiki first run completed.
```

If you prefer Docker:

```bash
docker compose run --rm first-run
```

## Browse the result in Obsidian

Open the repository root as a vault. Start with these generated demo files:

```text
demo/reports/dashboard-snapshots/sales-today.md
demo/reports/dashboard-snapshots/deal-risk.md
demo/reports/digests/my-day-ae.md
```

The Sales Today snapshot links to the underlying deal and lead cards. Open a row
and follow its `[[wikilinks]]` to the company, people, calls and tasks.

The demo is safe to inspect because its cards are clearly marked:

```yaml
dataset: demo
synthetic: true
```

The generator can rebuild that contour. No real customer data is needed.

## Take a guided product tour

The public [Knowledge Workbench](https://knowledge-workbench-seven.vercel.app/)
is the quickest way to inspect the synthetic interaction model before running
anything locally. Select **Tour** in the top bar. The recommended six-step
route takes about 90 seconds and follows one operating loop: role-shaped Today,
role contrast, account context, evidence, a cited assistant and governed Review.
The 12-step technical route also covers safe search, graph controls, local-only
monitoring and controlled import. Focused role tours contain only the workflows
that person can use.

Watch for the wiki model underneath the interface. The role views are derived
from the same linked cards, evidence remains attached and Review records the
route by which a proposed conclusion may enter shared knowledge.

The tour opens real demo views, but it never submits a proposal, saves a
monitoring plan or changes a card. It is a guided explanation of the system,
not a production login flow.

## Ask through an MCP client

Generate three client entries with different roles:

```bash
.venv/bin/python scripts/generate_mcp_demo_config.py \
  --personas ae,marketing,curator
```

Copy the generated `mcpServers` block into your MCP client and restart it. The
entry launches `saleswiki_mcp.server` over stdio. It is not an HTTP service.

Try these questions:

```text
What should I do today?
Brief me on BluePeak Energy.
Which deals are at risk?
```

Run the BluePeak question through the account-executive and marketing entries.
The account executive can see sales details allowed by policy. Marketing receives
a sanitized view. Personal data stays behind a `restricted://` handle.

The fixture actor comes from a server-side environment variable. This prevents
the caller from choosing a role inside a tool request, but it is still demo
identity. Shared production use needs per-request SSO.

## Run checks separately

The first-run command is convenient, but each check is also available on its own:

```bash
.venv/bin/python scripts/public_release_review.py
.venv/bin/python scripts/health_check.py
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/demo_dryrun.py
```

Docker runs the same checks in isolated, read-only-root-filesystem containers:

```bash
docker compose run --rm check
docker compose run --rm health
docker compose run --rm test
docker compose run --rm demo
```

After changing cards, rebuild the derived projections and dashboard snapshots:

```bash
python3 scripts/refresh.py
python3 scripts/refresh.py --demo
```

Do not edit generated files under `indexes/` by hand.

## Keep the data boundary in place

The health check fails if a `pilot/` directory or a file marked `dataset: pilot`
appears inside the public repository. Platform scripts accept explicit source and
output roots, and the gateway reads the private location from
`SALESWIKI_VAULT_ROOT`.

## Start a private pilot carefully

Do not copy real CRM exports or transcripts into this repository. Create a
separate access-controlled vault with no public remote. Keep personal-data bodies
out of Git. Use external restricted references where needed.

The repository includes a pilot runbook at:

```text
docs/engineering/permissioned-knowledge-pilot-runbook.md
```

The smallest useful pilot tests one repeated decision. The current runbook starts
with `lead_priority`: can a user get a better, faster, cited answer about what to
do today than from the current CRM and manual notes? This is the first measurable
sales workflow, not the limit of the product. It differs from Part 3's account-follow-up example; a real pilot would choose one decision and keep it fixed. A later marketing pilot can apply
the same method to a recurring campaign or content decision once its evidence
and success criteria are explicit.

A useful pilot should prove more than document retrieval. Continue only if real
work validates all four points:

1. Users prefer the cited extract-only answer for the chosen decision.
2. At least one correction benefits from proposal, approval and controlled apply.
3. Owning the policy and data plane solves a real operating requirement.
4. Users can explain why they chose the action and what evidence would change it.

If the pilot mainly proves that people want document search or summarization, an
existing product may be the cheaper answer.

Before the first real account enters the pilot, write down the research
contract: the repeated decision, the permitted evidence, the current workflow,
and the outcomes that would make the pilot stop or change direction. A claim
without a source, a role receiving restricted information, or a person unable
to explain the proposed action should count as a failed case. Do not change the
source scope, role rules, and answer wording all at once; otherwise the team
will not know what caused an improvement or a failure.

I would also record what happens when a fact needs review. A stale flag tells
us that a review window passed; by itself, it does not tell us whether a source
changed, a sync failed, or no one owned the task. In the private pilot log, I
would note when the check was due, noticed, assigned and resolved; the review
result; the likely cause (or `unknown`); and whether it could have changed the
decision. I would keep customer text and contact details out of that log, using
only a private record handle and a restricted source link.

That distinction follows public data-quality guidance: assess quality against
the intended use, track recurring issues, and investigate causes before choosing
a fix. The [Government Data Quality Framework](https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework-guidance)
describes that loop, and its [issues framework](https://www.gov.uk/government/publications/implement-a-data-quality-action-plan/data-quality-issues-framework)
puts impact and priority into the response. This is a method for the pilot to
test; it is not a claim that SalesWiki currently diagnoses stale records.

For an early pilot, I would use the roles and team boundaries already in place.
The person responsible for an account sees the next check; RevOps or a curator
can review process patterns within their existing access; department leads see
team-level summaries. I would not create a broad audit role until a multi-user
pilot shows a real need for independent review. If that need appears, it should
be read-only and limited to quality-event metadata, not customer content.

## What production deployment still needs

Before shared production use, add:

- per-request SSO or broker-issued identity;
- connector credential storage and least-privilege scopes;
- backup and restore drills;
- hosted logs, monitoring and rate limits;
- incident response;
- an external erasable store for personal-data bodies.

The public Compose preview runs its checks and demo MCP gateway with a read-only
root filesystem; only the named runtime volume is writable. A production setup
must deploy the worker separately and give only that process a controlled write
mount for the private vault. Docker does not replace authorization or identity.

## A practical evaluation checklist

After one hour with the demo, you should be able to answer these questions:

- Can I trace each answer back to a card?
- Can sales and marketing navigate the same linked account model without keeping
  separate copies of the shared context?
- Does a missing company produce `not-found` instead of a guess?
- Do two roles receive different allowed views of the same account?
- Can the gateway propose a correction without writing the card?
- Does the worker apply only an approved proposal?
- Can I regenerate indexes and dashboard snapshots from the Markdown source?
- Is real pilot data physically outside the public repository?
- Can the team distinguish an old source from a missed sync or an unowned review, and say when it cannot?

If those properties match your requirements, clone the
[SalesWiki repository](https://github.com/artemrudenko/SalesWiki-public) and run
the demo. Then choose one repeated sales or marketing decision and compare the
cited workflow with the way the team handles it today. That comparison, including
where SalesWiki gets in the way, is the evidence the next version needs.

## Continue the series

**Previous:** [What should a sales knowledge base help someone decide?](https://dev.to/artemr_rudenko_0bf2c2c505/what-should-a-sales-knowledge-base-help-someone-decide-saleswiki-part-3-of-5-pb0)

**Next:** *When does an integration help a sales decision?*
