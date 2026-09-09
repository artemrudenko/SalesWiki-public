---
title: Why I built a sales and marketing knowledge base that refuses to guess
published: false
description: I am exploring how sales and marketing teams can turn scattered context into cited decisions without letting AI fill the gaps.
tags: sales, marketing, knowledgebase, ai
series: Building SalesWiki in the open
cover_image: https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/devto-01-evidence-flow.png
---

Sales and marketing context rarely disappears in one big failure. It leaks away
in small pieces.

A useful detail stays in a call transcript. A pricing objection lives in a CRM
note. Market research sits in one document that nobody opens before the next
meeting. Then someone asks:

> What should we do next — and why?

I built [SalesWiki](https://github.com/artemrudenko/SalesWiki-public) to test a
simple idea: a shared knowledge base should help a person find the relevant
evidence and narrow the options without inventing what it does not know.

The durable source of truth is a folder of Markdown files that opens directly in
Obsidian. Raw evidence stays separate from compiled knowledge. Answers copy facts
from named fields and sections, attach citations, and say `not-found` when the
vault has no evidence.

SalesWiki is not a CRM and it is not a hosted SaaS. It is an open starter kit
for a governed sales and marketing knowledge base.

## This started as a research question

I did not begin with "let's build another knowledge product." I wanted to
learn whether a plain wiki could help sales and marketing teams make decisions
without becoming an unstructured folder. I also wanted to know whether agents
could maintain it without changing protected facts behind the scenes.

Sales and marketing are a useful stress test. Evidence arrives in many forms,
ages quickly and has mixed sensitivity. The result has to support a decision,
not simply retrieve a paragraph. A good answer should say what matters, where a
fact came from, how fresh it is and what the user can do next.

That led to four questions:

1. Can typed Markdown be a small but dependable knowledge data plane?
2. Will people trust a shorter cited answer more than a fluent generated one?
3. Can I make agent changes reviewable and reversible?
4. When does owning this machinery beat buying search over existing documents?

The synthetic demo answers only the engineering part. A real pilot still has to
prove that people prefer the workflow.

## One knowledge model, different views for each role

"Central" does not mean copying every CRM field, transcript and document into
one unrestricted folder. Those systems can remain the source of their original
records, and sensitive material can stay in a separate protected store.

SalesWiki centralizes the team's compiled understanding. A company, person,
deal, call, campaign, source or reusable case becomes a typed card with stable
links to related cards. Sales and marketing use the same account map, while
policy determines which cards and fields each role can read.

The layers have different jobs:

- raw evidence is preserved instead of silently rewritten;
- linked cards hold the current shared conclusion;
- proposals, review records and Git history show how that conclusion changed;
- indexes and dashboards are generated views that can be rebuilt from the cards.

Raw evidence stays as captured. The shared conclusion can change, but only
through a proposal, review and controlled apply step that leaves the earlier
evidence and the reason for the change visible.

This is why I chose a wiki model. The goal is not a larger folder. It is a
durable map that people and tools can navigate, question and correct.

## A small synthetic example

The public demo contains a synthetic deal for Atlas Robotics. Its problem is
simple: the next step has no confirmed owner. The deal card points to the demo
call and lead cards, labels the confidence as medium, and suggests a follow-up
to confirm the success criteria.

The useful part is not that the system chose for the account executive. It made
the reason for a proposed action inspectable. A person can follow the links,
challenge the evidence or decide that another option is better.

## The folder is simple on purpose

The core flow looks like this:

![Calls, CRM notes and research become immutable evidence, typed Markdown cards, generated indexes, dashboards and cited MCP answers](https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/diagrams/saleswiki-knowledge-flow.png)

The repository separates five areas of work:

| Folder | What belongs there |
| --- | --- |
| `raw/` | Original calls, exports, notes and research evidence |
| `wiki/` | Typed cards for companies, people, leads, deals, calls and reusable knowledge |
| `indexes/` | Rebuildable search, freshness, temporal and graph projections |
| `state/` and `tracking/` | Intake, review queues, processed sources and audit traces |
| `demo/` | Synthetic data that is safe to inspect and regenerate |

This choice has an obvious trade-off. A Markdown vault cannot hide behind a
database schema. The structure must be explicit and checked.

SalesWiki treats every card type as a small contract. A deal card has known YAML
properties and required sections. A health check fails when templates,
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

People can read this file. Git can diff it. Obsidian can link it. A script can
validate it. The permissioned gateway can extract its fields without asking a
model to reconstruct the deal from loose prose.

![A short tour of the SalesWiki Workbench, from a role-specific priority to linked account context and evidence](https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/tours/saleswiki-tour-teaser.gif)

## Why answers are extracted instead of generated

SalesWiki makes a deliberate trade-off in its permissioned core: an incomplete
cited answer is safer than a confident invented one.

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

The fastest way to see the idea is the six-step guided tour in the
[synthetic Knowledge Workbench](https://knowledge-workbench-seven.vercel.app/).
It starts with a role-specific priority, opens the account context and follows
the evidence to a proposed next step. The data is synthetic and the tour never
changes a card.

If you want to inspect the files and run the checks locally, Part 3 contains the
full fresh-clone and private-pilot path. That separation is deliberate: this
article explains why the model exists; the next practical article explains how
to test it safely.

## Demo boundary

The public Workbench uses synthetic data. It is a preview of the workflow, not
a system that makes commercial decisions. A suggested next step is a prompt for
review: the responsible person must check the cited records, the current context
and their own company policy before acting.

## Where to take it next

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

## Continue the series

**Next:** *How I keep shared sales knowledge safe for different roles* asks what
must change when the same account map serves sales, marketing and curators.

Repository: [SalesWiki](https://github.com/artemrudenko/SalesWiki-public)
