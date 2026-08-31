---
status: Accepted
date: 2026-07-03
deciders: SalesWiki maintainers
---

# ADR-0017: LLM is a labeled client-side layer; the gateway never generates

## Status

Accepted

## Context

ADR-0012 fixed the Answer Contract as extract-only: the permissioned gateway
cites card values and never generates prose, which makes accuracy a structural
property instead of a model behavior. But users still want model intelligence —
summaries, prioritization, "what should I do first" — and the demo needs an
honest answer to "where is the AI?". Different delivery tracks also have
different LLM realities: an MCP client (Claude Desktop / Cowork) *is* an LLM,
while the Rocket.Chat bridge is a headless poller with no model of its own.
That produced a confusing implicit rule about when an `ANTHROPIC_API_KEY` is
required and when it is not, documented nowhere as architecture.

## Decision

We keep every generative step **outside the trust boundary**, in the client
layer, and we label it. Concretely:

- The core, the MCP gateway and the worker never call an LLM and never need an
  API key. Their output is extracted, cited card data (ADR-0012).
- An LLM may **rephrase or rank** a finished, role-gated Answer envelope in the
  client layer, under a "use only these facts" prompt. Every such block is
  explicitly marked in the output (`🤖 Summary (from card data)`,
  `🧠 Recommendations (AI-generated from the cited data above)`), is opt-in via
  env flags (`RC_LLM_SUMMARY`, `RC_LLM_RECS`), and silently degrades (to a
  deterministic composition, or to absence) on any failure.
- A key is therefore required only where our own code must call a model —
  today the headless Rocket.Chat bridge; an MCP client brings its own model and
  needs nothing from us. Keys live outside the repository (shell env/Keychain).

The canonical usage table lives in
[llm-usage-architecture](../engineering/llm-usage-architecture.md).

## Consequences

**Positive**
- Access control and accuracy never depend on model behavior: the LLM sees only
  an envelope the policy engine already shaped for that role.
- The demo answer to "where is the AI?" is honest and demonstrable: facts are
  extracted, intelligence is layered on top with a visible label.
- Any client (chat, MCP, future web) can add or drop the generative layer
  without touching the core.

**Negative / trade-offs**
- Two rendering paths (deterministic + LLM) must be kept consistent; the
  deterministic summary is noticeably weaker than the model one.
- The grounding rule is prompt-enforced, not structurally enforced — a model
  could still misphrase a cited fact; the label and the cited envelope below it
  are the mitigation.
- Per-answer model calls add ~1–2 s latency and per-call cost in chat.

## Alternatives considered

- **LLM inside the gateway** (generate the answer from retrieved cards) —
  rejected: reintroduces hallucination risk into the trust boundary and makes
  role-shaping auditability model-dependent.
- **No LLM anywhere** — rejected: digests without prioritization bury the
  action; the demo loses its "AI on top of governed data" story.
- **Always-on LLM (no flags)** — rejected: the demo must run offline and
  deterministically without a key, and never break on API failure.

## References

- `integrations/rocketchat/bridge.py` (`_llm_call`, `_llm_summary`,
  `_llm_recommendations`, markers)
- [ADR-0012](0012-answer-contract-extract-only.md) — the extract-only base
- [llm-usage-architecture](../engineering/llm-usage-architecture.md)
- `integrations/rocketchat/README.md` — flag-level documentation
