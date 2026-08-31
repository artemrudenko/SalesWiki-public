---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0012: Answer Contract: extract-only, never generate, mandatory citations

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

The permissioned-knowledge gateway answers business questions for non-technical
employees over sensitive sales/marketing data. A free-text LLM-generated answer
would be unverifiable: it could hallucinate a deal value, blur which boundary a
fact came from, or invent a confident answer when the vault has nothing. For a
system whose whole point is governed, cited, access-aware knowledge, the answer
itself has to be accurate by construction and honest when it cannot answer. This
was standardized in Slice 10 (Answer Contract) and implemented in
`saleswiki_mcp/answer.py`; the architecture doc fixes the required answer shape.

## Decision

We make every read tool return one Answer Contract envelope
(`saleswiki_mcp/answer.py`): structured fields (conclusion, sections, citations,
confidence, freshness, as_of, next_action, missing, access) plus deterministically
rendered Markdown, with record lists rendered as tables. The core extracts cited
values from cards and never generates prose: accuracy is by construction. Every
non-missing section carries provenance (a `Citation` naming the boundary and
path/handle), and when the vault has no data the tool returns an honest
`not-found` answer with an explicit Missing note and no filler — rather than a
plausible-sounding guess. Field extraction is driven by `schemas/field-extraction.json`
(type → field → section/label), not hardcoded card strings, so the gateway can
serve a differently-shaped vault by swapping the profile.

## Consequences

**Positive**
- Answers are verifiable: every claim traces to a cited card, so no hallucinated
  facts and no uncited assertions.
- "I don't know" is a first-class, honest outcome (`Answer.not_found`), so absence
  of data never becomes a confident wrong answer.
- One predictable envelope across all read tools makes output testable and
  consistent for downstream clients (chat, UI) and renderers.
- Decoupling extraction from card shape lets a real-vault pilot reuse the gateway
  by swapping the extraction profile.

**Negative / trade-offs**
- Answers are only as expressive as what cards literally contain — no synthesis or
  inference across cards, which can read as terse (intended, for trust).
- Adding a new fact to an answer means adding it to the card and the extraction
  profile, not just prompting a model.
- A separate, opt-in LLM summary layer (deterministic by default) sits strictly on
  top of the cited envelope and may not introduce uncited content.

## Alternatives considered

- **LLM-generated free-text answers** — rejected: unverifiable, can hallucinate,
  and would blur access boundaries and provenance.
- **Best-effort answer with a plausible guess on missing data** — rejected in favor
  of an explicit `not-found`; a confident wrong answer is worse than an honest gap.
- **Hardcoding field locations per card type** — rejected for the field-extraction
  contract so the same gateway can serve a differently-shaped (real pilot) vault.

## References

- `saleswiki_mcp/answer.py` (`Answer`, `Citation`, `not_found`, `render`)
- `schemas/field-extraction.json`
- [[permissioned-knowledge-architecture]] (Answer Contract, Overlay rules)
- [[permissioned-knowledge-field-extraction]]
- `CHANGELOG.md` ([0.2.0] → Answer Contract envelope)
