---
title: Buy vs Build — the three reasons to build SalesWiki
tags:
  - process
  - architecture
  - strategy
status: active
updated: 2026-07-06
---

# Buy vs Build

For a 10–15-person go-to-market team, buying is the default. Notion, Glean,
HubSpot and general-purpose AI connectors already provide useful combinations
of permissions, search, citations, CRM enrichment and familiar user interfaces.
SalesWiki is justified only if the team needs the three differentiators below
**together** and validates them on real work.

> [!important] Decision rule
> “Search our knowledge with AI” is not a reason to build SalesWiki. Build only
> when deterministic evidence, governed changes and an owned data plane are hard
> requirements whose value exceeds the operating cost.

## The Three Real Differentiators

### 1. Deterministic, extract-only answers

SalesWiki answers from named card fields and sections, carries mandatory
citations, reports freshness and returns an honest `not-found` when evidence is
missing. The gateway does not generate missing facts. Role filtering happens
before any answer or optional client-side LLM sees the content.

This is stricter than permission-aware generative enterprise search. Notion
Enterprise Search and Glean AI Answers already advertise permission-respecting
answers with citations; those capabilities are therefore **market baseline, not
SalesWiki differentiation**:

- [Notion Enterprise Search](https://www.notion.com/en-gb/product/enterprise-search)
- [Glean AI Answers](https://docs.glean.com/user-guide/assistant/ai-answers)

SalesWiki should be built for this reason only if a wrong synthesis is materially
more costly than an incomplete answer, and users prefer cited extraction over a
more fluent generative response. See ADR-0012 and
[[permissioned-knowledge-architecture]].

### 2. Governed change control, not ordinary page editing

SalesWiki treats a knowledge change as a controlled transaction:

```text
proposal → review → signed approval → single-writer apply → validation/audit → rollback
```

The gateway cannot directly mutate production cards. Approval is bound to the
exact payload, and changes land in `Review Needed` rather than silently replacing
controlled identity fields. This is different from page history, comments or a
generic workflow layered onto a wiki.

This differentiator matters when the team must prove who proposed, approved and
applied a sensitive change, or when CRM/writeback fields need a controlled
boundary. It does not matter enough for ordinary collaborative note editing.
See ADR-0011, ADR-0015 and [[entity-card-governance]].

### 3. An owned, portable data plane

The durable source of truth is Markdown, JSON and rebuildable indexes under the
team’s control. Schemas, scoring, access policy and answer extraction are
configuration that can be inspected, versioned and moved without exporting a
vendor database. Sensitive bodies can stay in an external erasable store while
the vault keeps governed handles.

This is more than “data export.” The team owns the semantic model, the policy
contract and the application path. The cost is equally real: the team also owns
maintenance, identity, backups, retention, connectors and incident response.
See ADR-0001, ADR-0018 and [[permission-boundary-blueprint]].

## What Is Not Differentiation

- Permission-aware search by itself: Notion and Glean already provide it.
- Citations by themselves: enterprise-search products already cite sources.
- CRM enrichment and lead data: HubSpot already provides native enrichment,
  buyer-intent and scoring capabilities
  ([HubSpot Credits and Breeze features](https://knowledge.hubspot.com/account-management/understand-breeze-intelligence-credits-and-billing)).
- A chat interface: any MCP/AI client can provide one.
- Obsidian or Markdown alone: portability is useful, but not enough to justify a
  permissioned service.
- “Our own AI”: the SalesWiki core is intentionally extract-only; optional
  generation lives in the client layer.

## Option Fit

| Need | Buy / use existing tools | Build SalesWiki |
| --- | --- | --- |
| Fast rollout, familiar UI, broad search | Strong fit | Weak fit |
| Native CRM workflows and enrichment | HubSpot is the better default | Integrate only where governance adds value |
| Permission-aware cited answers | Notion/Glean already cover much of this | Build only for the stricter extract-only contract |
| Exact proposal/approval/apply/rollback chain | Usually requires adaptation | Core differentiator |
| Inspectable, portable policy and semantic model | Vendor-dependent | Core differentiator |
| Low operating overhead | Strong fit | Weak fit |
| Custom mixed-sensitivity sales workflows | Limited by product model | Strong fit if validated |

## Investment Gate

Before expanding SSO, connectors or card types, run the four-week
`lead_priority` pilot in [[permissioned-knowledge-pilot-runbook]]. Continue the
build only if the pilot shows that:

1. users repeatedly choose the cited extract-only answer over the current
   HubSpot/Obsidian workflow;
2. at least one real correction benefits from the governed change loop;
3. ownership/portability is a stated operational or compliance requirement,
   not a theoretical preference;
4. the value exceeds curator and maintenance time.

If the pilot mainly validates search, summarization or enrichment, buy or extend
the existing stack. If it validates all three differentiators, proceed with one
read-only inflow connector and real identity before adding breadth.

## Reassessment Triggers

- Re-run the market comparison before a production purchase/build decision;
  vendor capabilities change faster than this architecture.
- Reassess if the team no longer requires deterministic extraction or exact
  write governance.
- Reassess when the operating team, connector count or compliance scope grows:
  enterprise search or a managed knowledge platform may become cheaper than
  ownership.

## References

- [[permissioned-knowledge-architecture]] — product risks and target architecture
- [[permissioned-knowledge-pilot-runbook]] — real-data validation gate
- ADR-0011, ADR-0012, ADR-0015 and ADR-0018
