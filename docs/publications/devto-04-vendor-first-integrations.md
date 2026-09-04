---
title: "How I am connecting SalesWiki without rebuilding every vendor integration"
published: false
description: "A vendor-first strategy for bringing CRM, document and chat context into SalesWiki without moving integration complexity into the knowledge core."
tags: mcp, architecture, opensource, python
series: "Building SalesWiki in the open"
cover_image: https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/assets/publication/devto-04-connector-paths.png
---

Once SalesWiki could assemble a cited answer for different sales and marketing
roles, the next question was where the context should come from. CRM records,
call notes, documents and conversations live in different systems. Connecting
them all could easily become a larger project than the knowledge workflow itself.

The first chat integration made that risk concrete. SalesWiki could answer
role-aware questions inside Rocket.Chat. Once that demo was running, it was easy
to imagine the next tickets: add Telegram, add Slack, add Teams, add HubSpot, add
Google Drive.

That list looks like progress. It can also turn a small project into five OAuth
implementations, five retry systems and five slightly different copies of the
same conversation state.

I paused and asked a simpler question: which parts does SalesWiki need to own,
and which parts should a vendor maintain?

The answer depends on the decision being improved. A connector earns its place
when it closes a specific evidence gap or shortens the path to a defensible
action. Connecting a system because it contains interesting data only widens
the search again.

## Four jobs that should not share one interface

The word "connector" hid several different jobs:

| Job | Examples | What it does |
| --- | --- | --- |
| Client surface | Claude, Slackbot, a Microsoft 365 agent | Calls SalesWiki MCP tools |
| Chat adapter | Rocket.Chat, Telegram | Moves messages and files between a chat API and SalesWiki |
| Source connector | HubSpot, Drive, Slack history | Reads evidence or structured records from another system |
| Notification sink | Slack digest, Teams digest, email | Sends an approved report or alert |

Identity is separate again. A Rocket.Chat user ID or Slack user ID can identify
a person, but it must never become a SalesWiki role by itself.

Trying to hide all four jobs behind a universal `ConnectorAdapter` would produce
a vague interface with many optional methods. I chose narrow contracts instead.

![MCP clients call SalesWiki, custom chats use a shared runtime, and controlled ingest uses official vendor MCP servers](https://raw.githubusercontent.com/artemrudenko/SalesWiki-public/main/diagrams/saleswiki-integration-platform.png)

## There are two MCP directions

This distinction cleared up most of the architecture.

In the first direction, a client calls SalesWiki:

```text
Claude / Slackbot / M365 agent
              |
              v
       SalesWiki MCP server
              |
              v
 role-aware, cited knowledge
```

In the second direction, a controlled SalesWiki process calls a vendor:

```text
approved ingest runner
        |
        v
HubSpot / Google / Slack MCP
        |
        v
staged evidence or proposal
        |
        v
approval -> single writer -> vault
```

The second flow is not allowed to write straight into a production card. Vendor
tools may simplify authentication and API access, but they do not replace the
proposal, approval and audit rules.

I also avoid putting broad vendor write tools next to SalesWiki tools in a
general-purpose client. Otherwise a user could skip the governed path and ask
the vendor tool to make the change directly.

## Rocket.Chat became a reference adapter

The original bridge mixed several responsibilities in one polling loop:

* reading provider messages;
* keeping the current role and account context;
* routing commands;
* uploading files;
* clearing history;
* running the demo sequence.

The bridge now sends normalized messages into a shared runtime. A session key
contains the provider, tenant, conversation, thread and external user. Provider
retries are suppressed by message ID with a bounded in-memory window.

The application returns typed actions:

```python
TextResponse("...cited answer...")
FileResponse("pipeline.csv", content, "text/csv")
StartDemo(delay_seconds=5)
ClearConversation()
NoReply()
```

Each provider declares what it supports. If a channel cannot upload a file or
delete history, the runtime says so. It does not pretend every chat has the same
features.

Adding a custom channel now means implementing a small protocol:

```python
class ChatAdapter(Protocol):
    provider: str
    tenant_id: str
    conversation_id: str
    capabilities: ChatCapabilities

    def receive(self, cursor: str) -> InboundBatch: ...
    def send_text(self, response: TextResponse, *, thread_id: str = "") -> None: ...
    def send_file(self, response: FileResponse, *, thread_id: str = "") -> None: ...
    def clear_conversation(self) -> tuple[int, int]: ...
```

The policy and knowledge core do not import chat integrations. An architecture
test checks that boundary.

## Configuration needed the same separation

Credentials do not belong in a tracked file. Provider behavior should not be
spread across a dozen shell variables either.

SalesWiki now uses four configuration layers:

| Layer | Example | Stored where |
| --- | --- | --- |
| Product contract | allowed scopes and write policy | tracked JSON schemas |
| Deployment profile | enabled adapter, mode and paths | external TOML |
| Secret value | password, token or OAuth secret | environment or secret manager |
| Runtime state | cursor, session, retry and audit data | configured runtime directory |

A demo profile looks like this:

```toml
version = 1
profile = "demo"

[vault]
root = "../demo/permissioned"
runtime = "../demo/runtime"

[chat]
session_store = "memory"
default_trigger = "?"

[chat.adapters.rocket-demo]
provider = "rocketchat"
enabled = true
mode = "poll"
identity_provider = "fixture"
url_env = "ROCKETCHAT_URL"
user_env = "ROCKETCHAT_USER"
password_env = "ROCKETCHAT_PASSWORD"
conversation = "saleswiki-demo"
```

The file contains names of environment variables, not their values. The CLI can
validate it and show a redacted view:

```bash
cp config/runtime.example.toml config/runtime.toml
export SALESWIKI_CONFIG=config/runtime.toml
python3 -m saleswiki_runtime config validate
python3 -m saleswiki_runtime config show --redacted
python3 -m saleswiki_runtime doctor
```

`config/runtime.toml` is ignored by Git and Docker. Legacy `RC_*` variables need
an explicit opt-in, so an old shell profile cannot make an accidental network
connection.

## What I plan to buy, reuse and build

My current choices are based on official product documentation:

| Need | First choice | Why |
| --- | --- | --- |
| Slack as a SalesWiki UI | connect Slackbot to the SalesWiki remote MCP server | avoid a second policy implementation |
| Teams / Microsoft 365 UI | use a Microsoft 365 agent connector | reuse the same SalesWiki tools |
| Interactive HubSpot read | evaluate the official HubSpot remote MCP server | start with vendor-managed CRM tools and OAuth |
| Scheduled HubSpot sync | official API, webhooks or a managed sync product | conversational MCP may not provide checkpoints and reconciliation |
| Google Drive / Docs read | limited official Workspace MCP experiment | the service is still Developer Preview |
| Rocket.Chat UI | keep the custom adapter | it already demonstrates the channel contract |
| Telegram UI | build only after real demand | a chat demo is not a reason to own another integration |

The official references are the [HubSpot remote MCP server](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server), [Google Workspace MCP servers](https://developers.google.com/workspace/guides/configure-mcp-servers), [Slack MCP server](https://docs.slack.dev/ai/slack-mcp-server/), [Slackbot MCP connections](https://slack.com/help/articles/52414744085139-Connect-Slackbot-to-other-apps-with-MCP/) and [Microsoft 365 agent connectors](https://learn.microsoft.com/en-us/microsoftteams/platform/m365-apps/agent-connectors).

## MCP is not automatically a sync engine

An MCP server can be excellent for an interactive question and still be the
wrong tool for nightly synchronization.

A real sync needs stable IDs, pagination, checkpoints, delta reads, rate-limit
handling, replay safety and reconciliation. If the vendor MCP does not expose
those controls, I will use its API, webhook support or a managed connector.

The decision order is:

1. Check the official vendor MCP.
2. Reject it if least-privilege scopes, identity, audit or safe failure behavior
   are missing.
3. Check the official API, webhooks or a managed connector.
4. Build a thin custom adapter only for the remaining gap.

For writes, the standard is higher. An approved external action needs an exact
payload hash, idempotency key, previous value, provider result and recovery path.

## The rollout order matters

I am not connecting every vendor at once.

1. The typed configuration and shared chat runtime are complete.
2. Next comes a hosted SalesWiki MCP endpoint with OAuth 2.1 and per-request
   identity. The local fixture identity will remain demo-only.
3. Slackbot or a Microsoft 365 agent can then test SalesWiki as a native MCP
   client.
4. The first source pilot will be read-only HubSpot, but only after the existing
   `lead_priority` pilot shows that the workflow saves useful time.
5. External CRM, email or calendar actions come last and stay worker-owned.

That order keeps infrastructure behind product evidence. It also gives each new
credential a named purpose.

## Pros and cons

The approach reduces provider code, keeps SalesWiki replaceable and lets Slack
or Microsoft maintain their own client experience. The shared runtime also makes
small custom channels cheaper when there is demonstrated demand for one.

There are costs. Vendor MCP tools can change, preview services are risky for
production, and an interactive tool catalog may be a poor fit for bulk sync.
Remote MCP also needs real OAuth, hosting, monitoring and tenant administration.

The escape hatch is deliberate: Markdown remains the durable source of truth,
derived indexes can be rebuilt, and every provider sits outside the core.

## Try the current part

The repository does not claim to ship production Slack, Teams or HubSpot
connections yet. It does ship the config loader, Rocket.Chat reference adapter,
architecture tests and synthetic end-to-end demo.

```bash
git clone https://github.com/artemrudenko/SalesWiki-public.git SalesWiki
cd SalesWiki
python3 scripts/first_run.py
python3 -m saleswiki_runtime --config config/runtime.example.toml config validate
python3 -m unittest tests.test_chat_runtime tests.test_code_structure
```

Read the implementation plan and ADR in the
[SalesWiki repository](https://github.com/artemrudenko/SalesWiki-public). If you
extend it, start with one validated sales or marketing decision and one read
scope. The connector has a job only when it supplies evidence for that decision
or returns the resulting answer where someone already works. An available API
is not enough reason to add another integration.

That completes the first arc of the series: define the decision, make its
evidence and access rules visible, test it on a narrow workflow, then connect
only the systems that the validated workflow needs.
