# SalesWiki Knowledge Workbench prototype

This is a local, interactive prototype of the graph-led SalesWiki Entity Explorer. It demonstrates how a non-technical sales or marketing user can understand one account, inspect the evidence behind a conclusion, ask a grounded question, and submit a governed update proposal.

The prototype defaults to synthetic in-browser fixtures. Set
`VITE_SALESWIKI_GRAPH_ENDPOINT=/api/v1/entity-graph` to use the optional local
Workbench BFF, which calls the real MCP stdio tool and returns a validated
GraphView. Neither mode embeds credentials, production authentication or
persistence in the browser.

## Run locally

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 4173 --strictPort
```

Open `http://localhost:4173/`.

## What to try

- Switch between the demo people to compare an AE’s owned-opportunity queue,
  SDR pipeline creation, Head of Sales / RevOps pipeline quality, curator
  evidence review, Marketing’s permitted signal view, and administrator
  governance work. The Today dashboard, visible accounts and Review entry
  point change with the synthetic role.
- Switch between BluePeak Energy, Atlas Foods, and Northstar Robotics.
- Filter the graph by people, deals, calls, or evidence.
- Select a node or an evidence-trace item to inspect its context.
- Search within the current account.
- Choose **Ask assistant** for a short set of focused, cited questions shaped
  around the current role. Marketing sees questions about usable context and
  the next marketing action instead of sales-only deal and call prompts. It is
  guided, not free-form AI chat.
- Use **Help** in the top bar for a short explanation of access, evidence,
  monitoring, review and the demo boundary. Small `i` icons explain the most
  easily misunderstood dashboard and assistant concepts.
- Submit a proposal and see it enter the review queue.
- Choose **Import** to turn a small CSV row or structured meeting note into
  reviewable drafts. A mismatch stops before submission; confirmation creates a
  proposal, not a card write.
- Choose **Review** to inspect the proposal inbox, open the related account and
  see whether the fixed server-side role may approve or return a proposal. An
  approval is queued for the separate worker; it does not edit a card from the
  browser.
- **Ask assistant** routes each selected question server-side to a real,
  role-aware cited read; **Propose an update** creates a governed
  `flag_stale_or_wrong` proposal.
- **History** and the monitoring plan are local to this browser. They improve
  the demo workflow but are not a replacement for the append-only audit ledger
  or a live connector.

## Why this scales without per-company artwork

Every account uses the same data contract and the same reusable node components. A future adapter converts vault cards or MCP answers into this contract; the graph library then lays out and renders the account. Adding a company means adding data, not designing another screen or generating another image.

The selected mock and the browser comparison captures are design evidence only. They are not part of the runtime experience.

The controlled-import boundary and its deliberate limits are described in
[`docs/engineering/workbench-controlled-import.md`](../../docs/engineering/workbench-controlled-import.md).
The review flow and its server-owned permissions are described in
[`docs/engineering/workbench-review-inbox.md`](../../docs/engineering/workbench-review-inbox.md).

## Trying roles honestly

The fixture mode is a synthetic, role-aware walkthrough: switching a person
changes the visible account context, role-specific daily queue, decision-signal
dashboard and review permission. Import
and update proposals share the same local Review queue so the full demo loop is
visible. The BFF mode exercises the real policy path with the same UI shape.
Neither mode is SSO: a production account picker and discovery data must come
from the server, never from a browser bundle.

## Production path

The layout-neutral MCP GraphView adapter described in [`docs/engineering/mcp-graph-adapter.md`](../../docs/engineering/mcp-graph-adapter.md) is implemented in the core and exposed over local stdio MCP. The demo-only BFF verifies the complete browser → MCP → policy → GraphView path with a server-resolved synthetic persona. When enabled in the demo configuration, the top bar can switch among allowlisted synthetic people through an opaque BFF session; it never accepts a client-chosen role. The remaining production step is hosted Streamable HTTP MCP with OAuth/SSO identity resolved per request. GraphView is a sibling of the Answer Contract rather than a parser over rendered answer text. Read operations remain role-aware and cited. Update actions remain proposals: review, authorization, single-writer apply, validation, and audit happen outside the browser.

Exact BFF and UI startup commands are in [`docs/DEPLOYMENT.en.md`](../../docs/DEPLOYMENT.en.md#knowledge-workbench-through-the-real-mcp-tool).

## Verification

```bash
npm run build
npm run test:sites
```

Visual comparison and interaction evidence are recorded in `design-qa.md`.
