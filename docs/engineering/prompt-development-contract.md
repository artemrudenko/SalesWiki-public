---
title: Prompt Development Contract - Optional LLM Presentation
tags:
  - engineering
  - llm
  - security
  - testing
status: ready
updated: 2026-09-12
---

# Prompt Development Contract — Optional LLM Presentation

SalesWiki does not treat prompts as authorization or as a hidden source of
facts. Prompts may only shape an optional LLM presentation of an already
authorized Answer Contract.

## What changes where

| Need | Artifact | Owner of the boundary |
| --- | --- | --- |
| Role and task framing | `schemas/presentation-profiles.json` | Client presentation layer |
| Personal tone, length and emphasis | Runtime user preferences | Client presentation layer |
| Facts, citations, freshness, `missing`, access | `saleswiki_mcp` Answer Contract | Gateway and policy |
| Model quality | Shadow evaluation against synthetic scenarios | Human reviewer |

Never put access rules, raw card data, private user instructions or an API key
into the schema. The core/gateway/worker remain extract-only.

## The prompt is assembled in four layers

1. **Fixed system boundary** — the model receives only the authorized Answer
   Contract and cannot retrieve, infer access, remove citations, hide
   freshness or `missing`, or make the final decision.
2. **Role framing** — the job's decision context: an account executive's next
   customer conversation, a marketing decision about an audience signal, a
   sales leader's intervention, Revenue Ops' confidence in the operating
   picture, or a curator's review decision.
3. **Task framing** — the immediate job such as `call_prep`, `deal_risk`,
   `lead_priority`, `my_day`, `pipeline_risk_digest`, `campaign_brief`, or
   `content_opportunities`. A task says which useful elements to foreground;
   it never changes the authorized facts.
4. **Personal presentation preference** — a validated choice of length, tone,
   emphasis and a short wording note. It is appended as the least authoritative
   layer. It cannot replace any of the first three layers.

`schemas/presentation-profiles.json` is the initial library. It is deliberately
small and maps tasks to the roles that make the decision, rather than giving
every role a generic prompt for every available read tool. Unknown combinations
fall back to the safe default presentation.

### How to evolve the library

Add a task only after naming the repeated decision it should improve. For each
role × task pair, write one sentence for the decision, the evidence that should
be prominent, the uncertainty that must stay visible, and the human choice that
remains. Add a synthetic scenario to
`tests/fixtures/presentation-prompt-scenarios.json` before enabling the prompt
for a live pilot.

Start personalisation with structured settings: compact or standard; direct or
analytical; emphasis on the next action, evidence, risks or audience. The short
free-text note is an optional supplement for wording preferences such as
"use short sentences". Do not expose a replace-the-system-prompt field.

## Safe editing loop

1. Change a role/task instruction in `schemas/presentation-profiles.json`.
2. Inspect the exact resulting system prompt without a model call:

   ```bash
   python3 scripts/render_presentation_prompt.py \
     --role marketing --task campaign_brief \
     --verbosity compact --tone analytical --focus audience
   ```

3. Run `python3 -m unittest tests.test_presentation_prompt_contract`.
4. Run the normal health check and the bridge tests.
5. If enabling a model, run a small synthetic shadow evaluation. Compare the
   deterministic answer, a profile-only result and a profile-plus-preference
   result. A reviewer checks that the generated block introduces no facts and
   leaves the cited answer intact.

## Acceptance criteria

- The prompt always says it may use only the supplied Answer Contract.
- It always denies the model authority over access and provenance.
- A user preference cannot request hidden data or removal of citations,
  freshness or missing information.
- The deterministic cited answer still renders if the model is off, fails or
  produces no usable output.
- Every evaluation scenario is synthetic until per-request SSO and a real pilot
  have been approved.

## What we do not need yet

No specialised external prompt-writing skill, prompt-management SaaS or
production LLM key is needed to refine these profiles. The current schema,
renderer and contract tests make changes reviewable. Add an evaluation provider
only after there is a concrete pilot question and success measure.
