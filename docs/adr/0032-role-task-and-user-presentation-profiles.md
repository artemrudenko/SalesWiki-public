---
status: Accepted
date: 2026-09-12
deciders: SalesWiki maintainers
---

# ADR-0032: Role, task and user preferences shape presentation after authorization

## Context

Different employees need different help from the same connected knowledge base.
An account executive preparing a call and a marketer planning a campaign should
not receive the same framing. Personalization must not become a route around
role and attribute-based access, the Answer Contract, or human review.

## Decision

We apply optional LLM presentation instructions only after the gateway has
returned an authorized, cited Answer Contract. A declarative role × task profile
sets the base framing. A user can add only validated presentation preferences:
verbosity, tone, emphasis and a short wording instruction. The role/task profile
and preferences are delivered as the client model's system instruction.

The core, gateway and worker remain extract-only. Preferences live in the
client runtime, never determine identity or authorization, and cannot remove
citations, freshness, missing data or the deterministic answer. Requests that
try to modify access or provenance are rejected.

## Consequences

**Positive**
- Each role receives a decision-relevant framing without gaining additional data.
- Users can tailor AI presentation without replacing shared evidence and review.
- The profile is inspectable and reviewable as a schema.

**Negative / trade-offs**
- This is a Rocket.Chat demo implementation; a shared deployment still needs
  authenticated per-request identity and a durable preference store.
- A prompt is not an authorization mechanism, so deterministic citations and
  answer rendering remain mandatory.

## Alternatives considered

- **Let users replace the role prompt** — rejected: it blurs authority and
  makes unsafe output behavior easier to request.
- **Put personalization in the gateway** — rejected: it would put generation or
  mutable user state inside the trusted extract-only boundary.

## References

- [ADR-0017](0017-llm-client-side-labeled-layer.md)
- `schemas/presentation-profiles.json`
- `integrations/rocketchat/_bridge_presentation.py`
- [llm-usage-architecture](../engineering/llm-usage-architecture.md)
