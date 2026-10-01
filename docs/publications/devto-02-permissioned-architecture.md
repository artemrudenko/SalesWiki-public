---
title: "How I keep shared sales knowledge safe for different roles — SalesWiki, Part 2 of 5"
published: false
description: How one shared account map can support sales and marketing without exposing every note, while keeping evidence, review and production changes separate.
tags: architecture, security, mcp, python
series: Building SalesWiki in the open
cover_image: https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/devto-02-trust-boundary.png
---

A salesperson and a marketer can open the same customer account and need different facts.

Before a customer call, the salesperson needs what was agreed and the next step. Marketing needs an approved customer signal it can use in a campaign. Both need the same account map. Neither needs every private note.

That is the tension I wanted to test in SalesWiki. A shared knowledge base should stop people rebuilding context in separate tools. It should not turn every record into one unrestricted summary.

The question is not only what a person may see. It is what they are trying to decide. One person may be preparing the next conversation; another may be deciding whether a customer signal can support a message. The useful answer is different, but both answers should lead back to dated evidence, show what is missing, and leave the decision with the person responsible.

I treated a request for information and a request to change information as different paths. An answer uses only permitted facts. A correction waits for review before anything changes.

![A request passes through server-side identity and policy before producing a cited answer or an approved, auditable change](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/y4f8119hxfkibxub2g4g.png)

## One question, two valid answers

Consider the shared account BluePeak Energy. The account executive asks, "What was agreed, and what could block the next step?" Marketing asks, "Which approved signal can support a useful message?"

The account is the same. The decision is not. A sales answer might say, “The next step was a technical review on Tuesday; the security questionnaire is still missing.” A marketing answer might say, “The customer agreed to a public webinar, but product claims still need approval.”

Each answer should show its sources, how current they are and what it cannot tell the reader. One answer helps move a commercial conversation forward. The other helps decide what can be said publicly. A shared knowledge base earns its place when it preserves that difference before an answer is assembled.

This is one logical knowledge model, not one unrestricted storage location. Stable links connect the broad and protected cards, while physical boundaries keep sensitive material out of a role's retrieval path. The user experiences a shared account map; the server decides which part of that map can be assembled.

The service processes the request in this order:

```text
request
  -> server-side identity
  -> role and account policy
  -> allowed storage areas
  -> filtered retrieval
  -> field extraction
  -> cited answer
```

The browser does not decide a person's role. The server does. In the demo, a server setting selects a test person. A production deployment still needs a real identity provider on every request; that is one of the documented gaps.

## A label in a card is not access control

This card property is useful metadata:

```yaml
access: sales-confidential
```

It does not stop a person or process from opening the file. SalesWiki keeps broad knowledge, sensitive sales notes, contact references and legal material in separate storage areas. The directory that holds a card determines its class. A card outside a known area is denied by default.

Roles set the broad boundary: which storage areas may this person read? Ownership and other account attributes narrow the result. An account executive may see sensitive cards for accounts they own, while a head of sales sees the wider team view.

Contact details do not belong in the shared vault. The broad knowledge layer keeps only an opaque reference such as:

```text
restricted://personal-data/demo-bluepeak-energy-lead-contact
```

An approved external store can resolve that reference later. This keeps access and deletion concerns out of the shared knowledge layer.

## A fixed answer format keeps the limits visible

After filtering, the service extracts named values from permitted card sections. A configuration file connects the shape of a card to the shape of an answer, rather than leaving that decision to a prompt.

Every answer has the same fields:

| Field | Purpose |
| --- | --- |
| `conclusion` | The direct result |
| `sections` | Extracted facts or record tables |
| `citations` | Source and location |
| `confidence` and `freshness` | How certain and current the source data is |
| `next_action` | The recommended operational step already stored in the card |
| `missing` | What the vault cannot answer |
| `access` | Allowed, sanitized, blocked, ambiguous or not found |

An optional language model can later turn the result into prose in a client. It may not introduce new facts. The service itself does not need a language model to produce the answer.

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

The proposal includes the target entity, requested change, source evidence, risk and base version. Approval and apply are separate steps.

The worker changes the compiled card, not the original source. Raw evidence stays as captured; a correction creates a new, reviewed conclusion with a clear reason and audit record.

The worker then checks the approved change and the current card version. It holds a file lock so only one writer runs at a time. The card is written safely through a temporary file and replacement. Failed work is set aside for review. Rollback is an explicit worker action.

Approved changes land in the card's `Review Needed` section. They do not silently overwrite protected profile fields.

This is slower than direct page editing. That delay is useful when the knowledge affects deal economics, identity fields, updates to customer records or access decisions. It would be unnecessary overhead for an ordinary team notebook.

## Why a single writer is enough

SalesWiki targets a small sales and marketing operating group, not millions of writes per second. At that scale, one writer gives a clear invariant:

> Every applied change passed through one ordered, reviewable path.

The design avoids distributed locking and merge machinery before the pilot proves that they are needed. The reading service can have read-only access to the vault, while the writing worker has controlled write access.

## The audit chain makes rewriting visible

Audit events are append-only and linked with cryptographic hashes. Each record carries the previous hash and its own hash. Rewriting or removing an earlier record breaks verification of the later chain.

This makes tampering visible; it does not make the system magical. Storage permissions, backups and external monitoring still matter. For a private pilot, SalesWiki can sign a checkpoint containing the verified record count and latest hash, then store that checkpoint and its key separately. That can reveal a clean deletion at the end of the chain. Version history is useful for card changes, but it does not show who read sensitive data. Reading needs its own audit in the service.

## Rules should be visible, not hidden in code

The project keeps rules for access, storage boundaries, identity, answer fields and external connections in configuration files. The intent is simple: changing a role map, a storage boundary or an answer field should not require rewriting the service. The health check validates that these rules still agree with the cards and dashboards.

The code follows the same boundary. A server interface carries requests into the service, while identity, policy, retrieval, answers, proposals, audit and the worker live in separate modules. Optional chat integrations depend on that core; the core never depends on them. This makes it possible to replace a chat client without moving the rules that protect access and changes.

## What the demo has tested

The end-to-end dry run uses a throwaway vault and checks:

- one role cannot see data reserved for another;
- sourced answers and an honest “not found” result;
- proposal, approval and worker apply;
- rejection, audit verification and rollback paths;
- the same answer format across read tools.

The architecture still has open production work. Test identity must be replaced by a real identity provider on every request. Approval records need production-grade identity and secret handling. Connector credentials, backups, rate limits and incident response need an operating environment outside the public repository.

This part answers one question: the same shared knowledge can support different decisions only when identity and policy filter retrieval before an answer is assembled, and when changes follow a separate governed path.

## Continue the series

**Previous:** [Why I built a sales and marketing knowledge base that refuses to guess](https://dev.to/artemr_rudenko_0bf2c2c505/why-i-built-a-sales-and-marketing-knowledge-base-that-refuses-to-guess-5fhm)

**Next:** [What should a sales knowledge base help someone decide?](https://dev.to/artemr_rudenko_0bf2c2c505/what-should-a-sales-knowledge-base-help-someone-decide-saleswiki-part-3-of-5-pb0)

The code and architecture decisions are available in the [SalesWiki repository](https://github.com/artemrudenko/SalesWiki-public).
