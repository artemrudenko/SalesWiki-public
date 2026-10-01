---
title: Method Library Pilot - Licensed Sources to Safer Task Framing
status: active-pilot
updated: 2026-09-17
---

# Method Library Pilot — Licensed Sources to Safer Task Framing

This pilot tests whether small, licensed method notes improve the **shape** of
optional LLM presentation prompts without weakening SalesWiki's deterministic
fact, citation, freshness or access boundary.

The operating intake process is [[method-library-intake]]. The architectural
decision is [[0033-licensed-method-library-is-not-a-fact-store]].

## Source Cohort 1

| Source | License | Stored form | Candidate task |
| --- | --- | --- | --- |
| [[Source - Introduction to Marketing - MKTG 34303]] | CC BY 4.0, exceptions noted | dated remote-reference manifest | `call_prep`, `campaign_brief` |
| [[Source - Foundations in Digital Marketing]] | CC BY 4.0, exceptions noted | dated remote-reference manifest | `campaign_brief` |

The public repository intentionally does not mirror the full books. Their
publishers identify separately licensed media; the manifests preserve the
canonical source, license and collection date. Full-text import is a separate
asset-audit decision.

## Initial Change

The presentation profiles add only two source-informed completeness lenses:

- `account-exec × call_prep`: meeting objective, decision-process question,
  open questions and preparation step must be grounded in supplied facts.
- `marketing × campaign_brief`: audience, value proposition, channel/asset and
  measurement appear as a testable structure only when the supplied facts
  support them.

No scoring, retrieval, source selection, Answer Contract, access or worker
behavior changes in this pilot.

## Evaluation

Use at least 12 synthetic scenarios, split evenly between the two tasks. For
each, compare:

1. current deterministic Answer Contract;
2. baseline presentation profile;
3. method-informed presentation profile.

Reviewers score each response for:

- groundedness: no invented buyer, pain, audience, proof or metric;
- decision completeness: objective/decision, open question and next check are
  visible when applicable;
- actionability: one smallest justified next step;
- provenance: citations, freshness and `missing` remain visible;
- restraint: weak or absent evidence remains a gap, not an assertion.

Adopt a note only if it improves completeness/actionability without any
groundedness or provenance regression. Otherwise revert the profile wording and
mark the note rejected with an explanation.

## Explicit Non-Goals

- training or fine-tuning a model on the books;
- treating educational sources as customer evidence;
- importing CC BY-NC/CC BY-NC-SA works into the public MIT repository;
- changing lead/deal scoring automatically;
- presenting a generic sales framework as a company-specific recommendation.
