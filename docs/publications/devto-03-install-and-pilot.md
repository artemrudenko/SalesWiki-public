---
title: From synthetic demo to safe pilot: test SalesWiki on one real decision
published: false
description: Run the SalesWiki preview, inspect its trust boundaries, and design a private pilot around one repeated sales or marketing decision.
tags: tutorial, opensource, docker, mcp
series: Building SalesWiki in the open
cover_image: https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/devto-03-safe-pilot.png
---

A broad product idea becomes useful only when it improves a repeated decision.
For SalesWiki, that means moving from "can the architecture work?" to "does this
help a sales or marketing team act with less searching and more confidence?"

The pilot therefore measures a search process, not the attractiveness of an AI
answer. Can a person move from a new signal to an action they can explain and
check faster? Can they see which options were ruled out by missing, stale or
restricted context?

I wrote this tutorial to take SalesWiki from a fresh clone to a working synthetic
demo. It also marks the point where you should stop before adding real customer
data.

The public preview has two practical modes today:

1. A local demo or single-operator pilot.
2. A Docker-based demo and check environment.

It is not a hosted multi-user service yet.

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

## Understand the three data contours

The public repository, the synthetic demo and a real pilot are separate on
purpose.

![The platform repository stores code and synthetic demo data. Real pilot data stays in a separate private vault, and the health check fails if pilot data leaks into the repository](https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/diagrams/saleswiki-data-contours.png)

| Contour | Location | Data rule |
| --- | --- | --- |
| Platform | Public SalesWiki repository | Code, schemas, templates and docs |
| Demo | `demo/` inside the repository | Synthetic cards only |
| Pilot | A separate private vault outside the repository | Real accounts, deals, contacts and transcripts |

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
sales workflow, not the limit of the product. A later marketing pilot can apply
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

If those properties match your requirements, clone the
[SalesWiki repository](https://github.com/artemrudenko/SalesWiki-public) and run
the demo. Then choose one repeated sales or marketing decision and compare the
cited workflow with the way the team handles it today. That comparison, including
where SalesWiki gets in the way, is the evidence the next version needs.

Part 4 follows the question that comes after a useful pilot: how should CRM,
documents and chat systems connect without moving vendor complexity into the
knowledge core?
