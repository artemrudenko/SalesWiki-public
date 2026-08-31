---
status: Accepted
date: 2026-08-31
deciders: SalesWiki maintainers
---

# ADR-0029: Ship a guided assistant before free-form LLM chat

## Context

Users need a conversational way to understand an account. A free-form model
would add ambiguity around intent, prompt injection, data sharing, cost and
source attribution before a real-data pilot exists.

## Decision

We expose `saleswiki.guided_answer` with a small fixed menu: account brief,
what changed, next step, deal risk and call preparation. The server routes each
intent to an existing cited, policy-filtered read. The browser submits only the
allowlisted intent and current company identifier; it cannot submit a prompt,
role or tool name.

## Consequences

**Positive**
- Useful chat-like workflow without an API key or model.
- Existing authorization and citations remain the source of every answer.
- Forms a safe UX and transport seam for a later client-side intent router.

**Negative / trade-offs**
- Users cannot ask arbitrary questions yet.
- Some intents share an underlying brief until a specialized read is justified.

## Alternatives considered

- **Free-form cloud LLM immediately** — rejected until consent, provider,
  retention, prompt-safety and cost controls are approved.
- **Client-selected MCP tools** — rejected because it weakens the server-owned
  request contract and expands the browser attack surface.

## References

- `saleswiki_mcp/service.py`
- `integrations/workbench/server.py`
- `docs/engineering/llm-usage-architecture.md`
