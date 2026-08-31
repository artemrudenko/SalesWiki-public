---
status: Accepted
date: 2026-08-30
deciders: SalesWiki maintainers
---

# ADR-0026: Gate the Workbench review entry point by a server-owned capability

## Context

The governed review queue contains operational proposal context that ordinary
contributors must not discover. Showing every synthetic persona a `Review`
navigation item promised an action they could not take and invited the browser
to fetch a queue that policy should deny. Hiding a link client-side alone would
not be a permission boundary.

## Decision

The demo-session payload includes the server-derived boolean `can_review`.
Only reviewer roles (curator, HoS, RevOps and admin) receive it and see the
Workbench `Review` entry point. The fixture review client returns an empty,
blocked queue to every other role; the real BFF continues to invoke the
role-bound MCP review tool, which independently denies non-reviewers.

The separate future `My requests` capability requires a dedicated server-owned
endpoint that returns only the authenticated actor's proposals. It is not
implemented by filtering an already retrieved shared queue in the browser.

## Consequences

**Positive**
- Contributors are not offered a misleading review action or other users'
  proposal context.
- The UI visibility hint comes from the same server-owned fixture identity as
  the MCP invocation.
- Fixture tests exercise both an empty denied queue and a reviewer queue.

**Negative / trade-offs**
- A contributor cannot yet inspect the status of their own proposals in the
  Workbench.
- `can_review` is a navigation hint; the MCP policy remains the enforcement
  layer and must stay authoritative under OIDC.

## Alternatives considered

- **Show `Review` to everyone and disable its actions** — rejected: it exposes
  an irrelevant destination and risks disclosing queue metadata.
- **Filter a shared queue in the browser into `My requests`** — rejected: data
  received by the browser has already crossed the boundary.
- **Hide the navigation item without changing the review response** — rejected:
  a direct request could still expose the queue.

## References

- `integrations/workbench/server.py`
- `prototypes/knowledge-workbench/src/graphClient.js`
- `prototypes/knowledge-workbench/src/App.jsx`
- `tests/test_workbench_bff.py`
- `prototypes/knowledge-workbench/tests/graph-client.test.mjs`
- ADR-0024
- ADR-0025
