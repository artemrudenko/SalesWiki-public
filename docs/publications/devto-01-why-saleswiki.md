---
title: Why I built a sales and marketing knowledge base that refuses to guess
published: false
description: I am exploring how sales and marketing teams can turn scattered context into cited decisions without letting AI fill the gaps.
tags: sales, marketing, knowledgebase, ai
series: Building SalesWiki in the open
cover_image: https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/devto-01-evidence-flow.png
---

Sales and marketing context rarely disappears all at once. It leaks away in
small pieces.

A useful detail stays in a call transcript. A pricing objection lives in a CRM
note. Market research sits in one document and the campaign plan in another.
Sooner or later, someone asks a practical question:

> What should we do next, and why?

The context may exist, but nobody can assemble it quickly or explain where each
part came from. That can block a sales call, an account decision or a campaign.

I started building [SalesWiki](https://github.com/artemrudenko/SalesWiki-public) to test a different operating model. The
durable source of truth is a folder of Markdown files that opens directly in
Obsidian. Raw evidence stays separate from compiled knowledge. Answers copy
facts from named fields and sections, attach citations, and say `not-found`
when the vault has no evidence.

SalesWiki is not a CRM and it is not a hosted SaaS. It is an open starter kit
for a governed sales and marketing knowledge base.

## This started as a research question

I did not begin with "let's build another knowledge product." I wanted to
learn whether a plain wiki could help sales and marketing teams make decisions
without becoming an unstructured folder. I also wanted to know whether agents
could maintain it without changing protected facts behind the scenes.

Sales and marketing are a useful stress test. Evidence arrives in many shapes,
ages quickly and has mixed sensitivity. The output also has to support a decision,
rather than retrieve a paragraph. A good answer should say what matters, where the
fact came from, how fresh it is and what the user can do next.

That led to four questions:

1. Can typed Markdown be a small but dependable knowledge data plane?
2. Will people trust a shorter cited answer more than a fluent generated one?
3. Can I make agent changes reviewable and reversible?
4. When does owning this machinery beat buying search over existing documents?

The synthetic demo answers only the engineering part. A real pilot still has to
prove that people prefer the workflow.

## The folder is simple on purpose

The core flow looks like this:

![Calls, CRM notes and research become immutable evidence, typed Markdown cards, generated indexes, dashboards and cited MCP answers](https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/diagrams/saleswiki-knowledge-flow.png)

The repository separates five kinds of work:

| Folder | What belongs there |
| --- | --- |
| `raw/` | Original calls, exports, notes and research evidence |
| `wiki/` | Typed cards for companies, people, leads, deals, calls and reusable knowledge |
| `indexes/` | Rebuildable search, freshness, temporal and graph projections |
| `state/` and `tracking/` | Intake, review queues, processed sources and audit traces |
| `demo/` | Synthetic data that is safe to inspect and regenerate |

This choice has an obvious trade-off. A Markdown vault cannot hide behind a
database schema. The structure must be explicit and checked.

SalesWiki therefore treats every card type as a small contract. A deal card has
known YAML properties and required sections. A health check fails when templates,
properties, dashboards or links drift out of shape.

Here is a shortened synthetic deal card from the demo:

```markdown
---
type: deal
entity_id: demo-deal-atlas-robotics-pilot
dataset: demo
synthetic: true
access: sales-confidential
stage: Proposal
amount: 25000
score: 89
score_band: hot
freshness: needs-action
---

# Deal: Atlas Robotics Pilot

## Deal Readout

- Main risk: next step needs owner confirmation.
- Next best action: book follow-up and confirm success criteria.
- Confidence: medium
- Evidence: demo call and lead cards.
```

A person can read this file. Git can diff it. Obsidian can link it. A script can
validate it. The permissioned gateway can extract its fields without asking a
model to reconstruct the deal from loose prose.

## Why answers are extracted instead of generated

Most AI knowledge tools optimize for a fluent answer. SalesWiki makes a
different trade-off for the permissioned core: an incomplete cited answer is
safer than a confident invented one.

Every read tool returns the same Answer Contract:

```json
{
  "title": "Deal risk",
  "access": "allowed",
  "conclusion": "Atlas Robotics needs action.",
  "sections": [],
  "citations": [
    {
      "boundary": "sales-confidential",
      "path": "wiki/entities/deals/Deal - Atlas Robotics - Pilot.md"
    }
  ],
  "confidence": "medium",
  "freshness": "needs-action",
  "next_action": "Book follow-up and confirm success criteria.",
  "missing": []
}
```

The example above is shortened for readability, but the shape comes from the
real `saleswiki_mcp/answer.py` contract. Each answer includes access, conclusion,
sections, citations, confidence, freshness, the next action and missing fields.
The rendered Markdown uses the same data.

If a user asks for a company that is not in the vault, the answer is direct:

```text
Conclusion: Cannot answer from the knowledge base.
Missing: No matching company card was found.
Next action: add or research the company.
Access: not-found
```

There is no fallback paragraph that guesses what the company probably does.

## Markdown alone is not the product

Using Markdown is useful, but it is not enough to justify another system. I
would tell most teams to buy an existing product if all they need is AI search
over documents.

SalesWiki makes sense only when three requirements matter together:

1. Answers must be extracted from cited evidence.
2. Sensitive changes need proposal, approval, apply and rollback steps.
3. The team wants to own the semantic model, policy and durable data files.

That third point has a cost. Owning the data plane also means owning backups,
identity, connectors, retention and maintenance. The repository does not hide
that work.

## Where the design helps and where it costs

| What I chose | Why it helps | What you pay for it |
| --- | --- | --- |
| Markdown source of truth | people can read it; Git can diff it; tools can parse it | queries and transactions are weaker than in a database |
| Typed cards and validation | extraction stays predictable and drift becomes visible | templates and schema changes need discipline |
| Extract-only answers | missing data stays missing and every claim can be traced | answers are less flexible than free-form generation |
| Access checks before retrieval | closed content never reaches answer assembly | identity and boundary rules need careful design |
| Proposal, approval and one writer | sensitive edits are reviewable and reversible | a correction takes more steps |
| Owned data and policy | the team controls portability and meaning | the team also owns operations and maintenance |

I treat these as design constraints rather than universal best practices. If
your main problem is finding a document, a mature search product is probably the
better choice.

## Try the synthetic demo

You need Git and Python 3.11 or newer. Obsidian is recommended for browsing the
vault, but the checks run without it.

```bash
git clone https://github.com/artemrudenko/SalesWiki-public.git SalesWiki
cd SalesWiki
python3 scripts/first_run.py
```

The first-run script creates a virtual environment, installs the MCP dependency,
checks the public snapshot, validates the vault and runs the permissioned demo
smoke test.

Then open the repository root as an Obsidian vault and inspect:

```text
demo/reports/dashboard-snapshots/sales-today.md
demo/reports/dashboard-snapshots/deal-risk.md
demo/reports/digests/my-day-ae.md
```

The demo data is synthetic. Each demo card is marked with `dataset: demo` and
`synthetic: true`.

To connect an MCP client, generate ready-to-paste configuration:

```bash
.venv/bin/python scripts/generate_mcp_demo_config.py \
  --personas ae,marketing,curator
```

Restart the client and ask:

```text
What should I do today?
Brief me on BluePeak Energy.
Which deals are at risk?
```

These are sales examples because they are the most complete demo path today.
The same knowledge model also supports marketing campaign briefs and content
opportunities from permitted pains, objections and account signals.

For a small B2B team, a bounded question is often more useful than a new dashboard.
The current Workbench starts with a short role-aware daily queue, then lets the
user open the account graph when they need context. It also shows an explainable
account temperature: hot, warm, cold or at risk, with a reason drawn only from
records that role may already see.

The same Workbench now adds a small decision-signal dashboard and a guided
assistant. The assistant deliberately offers focused, cited questions rather
than a free-form chat box, so a user can inspect what changed or choose a next
step without turning access-controlled data into an opaque prompt.

One small interface lesson changed the demo as I built it: a role switch has to
change the job, not just an access badge. The synthetic account executive,
marketing and curator views therefore have different permitted accounts, daily
queues, decision signals and review access. In the public static Workbench, the
switcher is a visible fixture comparison, not authorization. The optional local
BFF resolves an allowlisted synthetic person on the server. In a shared
deployment, both demo mechanisms are replaced by SSO.

The public Workbench has a guided tour because screenshots were not enough to
explain this contrast. The recommended six-step route follows one decision from
a role-specific priority to account context, evidence, a bounded assistant and
curator review. The 12-step technical route also covers safe search, graph
controls, local monitoring and controlled import. Focused role tours contain
only the workflows available to that person. The tour opens real demo screens
but does not submit a proposal or change a card.

If you want to see the interface before cloning, open the
[synthetic Knowledge Workbench](https://knowledge-workbench-seven.vercel.app/).
It contains no customer data and makes its demo mode explicit.

The demo includes a Polish starter panel for teams that want to try the flow
without migrating a CRM. It is deliberately small: add one company, capture the
last conversation and its next step, then check the daily queue. Account
monitoring is currently a local configuration step, not an automatic news feed
or an external connector.

Ask the same question as an account executive and as marketing. The difference
is enforced before the answer is assembled, not added later by a prompt.

## If you want to develop it further

Start narrower than the repository looks. Pick one repeated decision, such as
"which lead needs action today?", and test it with a private vault.
Keep that vault outside the public checkout.

Then measure three things:

- does the user prefer the cited answer to the current CRM-and-notes workflow?
- how often does someone correct the compiled knowledge?
- how much curator time does the system consume each week?

Add SSO before shared multi-user use. Keep authorization before retrieval and
keep durable writes behind the worker. Add connectors or vector search only when
the validated workflow needs them. Otherwise it is easy to build impressive
infrastructure around an unproven habit.

## Where the public preview stops

The repository includes a synthetic demo, a local MCP gateway, a single-writer
worker, Docker checks and connector contracts. It does not yet include production
multi-user SSO, live HubSpot or Google Drive sync, hosted operations, or an
external erasable personal-data store.

That boundary matters. Fixture identities are useful for a demo and a
single-operator pilot. They are not production authentication.

This is the first part of the learning path: can a small owned knowledge layer
turn scattered context into a decision someone can check? Part 2 asks what must
change when the same context serves sales, marketing and curators with different
permissions. Part 3 moves the idea from a synthetic demo to one private pilot.

Repository: [SalesWiki](https://github.com/artemrudenko/SalesWiki-public)
