---
status: Accepted
date: 2026-08-29
deciders: SalesWiki maintainers
---

# ADR-0020: Prefer vendor MCP and native clients before custom integrations

## Status

Accepted

## Context

SalesWiki has a custom Rocket.Chat demo bridge and planned HubSpot, Google
Drive/Meet, Slack/email and identity integrations. The MCP ecosystem now includes
official remote servers from several relevant vendors, while Slackbot and
Microsoft 365 agents can invoke external MCP servers. Building a custom bot or
API client for every provider would duplicate authentication, scopes, rate-limit
handling and product-specific behavior.

Vendor availability alone is not sufficient. SalesWiki requires authorization
before retrieval, cited and deduplicated evidence, governed writes, an audit
chain and safe failure behavior. An MCP server optimized for interactive agent
use may also be a poor scheduled-sync engine.

## Decision

We use a vendor-first decision path:

1. evaluate the official vendor MCP server;
2. if it fails a mandatory security, identity, evidence or reliability gate,
   evaluate the official API/webhook or a managed connector;
3. build a custom provider adapter only for a documented remaining gap.

For collaboration products that can act as MCP clients, we first expose the
SalesWiki remote MCP server to their native agent surface. We build a custom chat
adapter only when the native MCP path cannot meet the required UX, identity or
deployment model.

Source connectors, chat adapters, notification sinks and identity providers
remain separate interfaces. All external writes remain behind SalesWiki's
proposal, approval, worker and audit path regardless of the provider transport.

## Consequences

**Positive**

- less provider-specific authentication and API code to maintain;
- faster access to vendor-supported scopes, audit and permission models;
- Slack and Microsoft 365 may reuse the SalesWiki MCP surface without duplicate bots;
- provider replacement does not change the Markdown vault or core service;
- build-vs-buy decisions become repeatable and evidence-based.

**Negative / trade-offs**

- vendor tools, plans, previews and schemas can change independently;
- MCP tool semantics may be less deterministic than a purpose-built sync API;
- official MCP servers may expose broader write capabilities than SalesWiki allows;
- remote MCP requires production identity, OAuth, hosting and operations;
- some channels, including Rocket.Chat and Telegram, still need custom adapters.

## Alternatives considered

- **Build one custom connector per vendor** — rejected as the default because it
  duplicates mature vendor functionality and creates unnecessary credential and
  upgrade ownership.
- **Use MCP for every integration** — rejected because scheduled sync, webhooks,
  reconciliation and exact writeback may be better served by official APIs.
- **Build a universal dynamic plugin framework now** — rejected until more than
  two real provider implementations prove that static interfaces are insufficient.
- **Keep Rocket.Chat-specific chat logic** — rejected because normalized messages,
  typed actions and session isolation are useful even if only one custom adapter remains.

## References

- [[integration-platform-plan]]
- [[connector-contracts]]
- `schemas/connector-contracts.json`
- `docs/engineering/permissioned-knowledge-architecture.md`
- ADR-0006, ADR-0011, ADR-0013 and ADR-0016
