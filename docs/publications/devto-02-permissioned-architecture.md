---
title: How I designed permissioned AI for a sales and marketing knowledge base
published: false
description: How SalesWiki gives different sales and marketing roles cited answers while keeping retrieval, proposals, approval and production writes separate.
tags: architecture, security, mcp, python
series: Building SalesWiki in the open
cover_image: https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/devto-02-trust-boundary.png
---

The first SalesWiki question was broad: can sales and marketing teams turn
scattered context into decisions they can check? The next question forced an
architecture choice. What happens when an account executive, a marketer and a
curator use the same knowledge but should not retrieve or change the same facts?

A read tool that can also edit production knowledge creates a large trust
surface. If the same process answers questions, interprets untrusted text and
writes cards, a bad instruction or a simple bug can move from retrieval to
mutation. Parallel writers add another problem: two valid edits can corrupt the
card or the audit sequence.

I separated those jobs in SalesWiki.

The MCP gateway can read, propose and govern. It cannot update production cards.
A separate worker is the only writer, and it applies only approved proposals.

![A user request passes through server-side identity and policy. Reads produce cited answers. Changes enter a proposal queue, curator approval, a single-writer worker, a transactional update and an audit chain](https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/diagrams/saleswiki-trust-boundary.png)

## One question, two valid answers

Consider this request:

> Brief me on BluePeak Energy.

An account executive may need pricing, the discount floor and competitor notes.
Marketing may need an approved company summary, public signals and a sanitized
case-study angle. Both users asked the same question, but they should not receive
the same fields.

The gateway processes the request in this order:

```text
request
  -> server-side identity
  -> role and attribute policy
  -> allowed storage boundaries
  -> filtered retrieval
  -> field extraction
  -> cited Answer Contract
```

The client cannot pass `role=admin` and gain more access. In the demo, a
server-side environment setting selects a fixture actor. A production deployment
still needs per-request SSO or OIDC, which is one of the documented gaps.

## A YAML label is not an access control

This card property is useful metadata:

```yaml
access: sales-confidential
```

It does not stop a person or process from opening the file. SalesWiki's target
model uses physical storage boundaries for broad knowledge, sales-confidential
data, personal-data handles and legal-review material. The boundary registry maps
paths to those classes. An unmatched path fails closed.

Role-based access control answers the broad question: which boundaries may this
role read? Attribute-based rules narrow the result. An account executive may see
sales-confidential cards for owned accounts while a head of sales sees the wider
team view.

Personal-data bodies do not belong in the Git-tracked vault. The broad knowledge
layer keeps an opaque handle such as:

```text
restricted://personal-data/demo-bluepeak-energy-lead-contact
```

An approved external store can resolve that handle later. This keeps access and
erasure concerns outside immutable Git history.

## The answer contract is deliberately strict

After policy filtering, the gateway extracts named values from allowed card
sections. The extraction profile lives in
`schemas/field-extraction.json`, so card shape and answer shape are connected by
configuration rather than a prompt.

Every answer has the same fields:

| Field | Purpose |
| --- | --- |
| `conclusion` | The direct result |
| `sections` | Extracted facts or record tables |
| `citations` | Boundary plus path or restricted handle |
| `confidence` and `freshness` | How certain and current the source data is |
| `next_action` | The recommended operational step already stored in the card |
| `missing` | What the vault cannot answer |
| `access` | Allowed, sanitized, blocked, ambiguous or not found |

Optional language generation can happen in a client, but it sits on top of the
cited envelope. It may not introduce uncited facts. The gateway itself has no LLM
dependency for answers.

## A change is a transaction, not an edit

Suppose a user spots an outdated deal risk. The visible workflow is:

```text
flag stale or wrong
  -> draft proposal
  -> review queue
  -> approve or reject
  -> worker apply
  -> validation and audit
  -> rollback if needed
```

The proposal includes the target entity, requested change, source evidence, risk
and base version. Approval and apply are separate steps.

The worker then checks the approved payload and the current card version. It
holds an operating-system file lock so only one writer runs at a time. The card
is written atomically through a temporary file and replacement. Failed work goes
to a dead-letter queue. Rollback is an explicit worker action.

Approved changes land in the card's `Review Needed` section. They do not silently
overwrite the protected `Controlled Profile` fields.

This is slower than direct page editing. That delay is useful when the knowledge
affects deal economics, identity fields, CRM writeback or access decisions. It
would be unnecessary overhead for an ordinary team notebook.

## Why a single writer is enough

SalesWiki targets a small sales and marketing operating group, not millions of
writes per second. At that scale, one writer gives a clear invariant:

> Every applied change passed through one ordered, reviewable path.

The design avoids distributed locking and merge machinery before the pilot proves
that they are needed. Gateway and worker can also receive different filesystem
permissions. The gateway can mount the vault read-only while the worker has the
controlled write mount.

## The audit chain makes rewriting visible

Audit events are append-only and linked with SHA-256 hashes. Each record carries
the previous hash and its own hash. Rewriting or removing an earlier record breaks
verification of the later chain.

This is tamper-evident, not magical. Storage permissions, backups and external
monitoring still matter. For a private pilot, SalesWiki can sign a checkpoint
containing the verified record count and head hash, then store that checkpoint
and its key outside the audit runtime volume. That detects a clean tail deletion
without pretending to be WORM storage. Git is also useful for card history, but
it does not tell you who read sensitive data. Read audit belongs in the service
layer.

## Configuration is part of the architecture

The project keeps several policies in machine-readable files:

```text
schemas/access-policy.json
schemas/boundary-registry.json
schemas/identity-provider.json
schemas/field-extraction.json
schemas/connector-contracts.json
schemas/scoring-models.json
```

The intent is simple: changing a role map, a storage boundary or a field extraction
profile should not require rewriting the gateway. The health check validates these
contracts and their relationship with templates and dashboards.

The code follows the same boundary. The MCP server is a transport adapter. A
service facade coordinates use cases, while identity, policy, retrieval,
extraction, answers, proposals, audit and the worker live in separate modules.
Optional chat integrations depend on that core; the core never depends on them.
This makes it possible to replace a client or transport without moving the
authorization and write invariants with it.

## What the demo proves

The end-to-end dry run uses a throwaway vault and checks:

- role contrast and no-leak behavior;
- cited answers and honest `not-found` results;
- proposal, approval and worker apply;
- rejection, audit verification and rollback paths;
- the same Answer Contract across read tools.

Run it locally:

```bash
python3 scripts/demo_dryrun.py
```

Or use Docker:

```bash
docker compose run --rm demo
```

The architecture still has open production work. Fixture identity must be
replaced by per-request SSO. Approval records need production-grade identity and
secret handling. Connector credentials, backups, rate limits and incident
response need an operating environment outside the public repository.

This part of the experiment answers one question: the same shared knowledge can
support different decisions only when identity and policy filter retrieval before
an answer is assembled, and when changes follow a separate governed path.

The code and ADRs are available in the [SalesWiki repository](https://github.com/artemrudenko/SalesWiki-public).
Part 3 tests the next question: how far can a synthetic demo take us before a
private real-data pilot becomes necessary?
