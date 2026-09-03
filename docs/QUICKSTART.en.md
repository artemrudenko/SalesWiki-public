# SalesWiki Quickstart (5 Minutes)

The fastest way to see SalesWiki working — on safe synthetic demo data, no real
customer information involved. Full setup lives in [SETUP.en.md](SETUP.en.md);
this page is the shortest path to first value.

## 1. What You Need

- Obsidian (free) — to browse the vault and dashboards.
- Python 3 — already present on macOS; needed for refresh scripts and the MCP gateway.
- Claude Code, Claude Desktop or Cowork — the primary way to ask questions in
  plain language (optional if you only browse in Obsidian).

## 2. See It (1 minute)

From the repository root, run the first-run assistant:

```bash
python3 scripts/first_run.py
```

It creates `.venv`, installs requirements, validates the public snapshot and
runs the permissioned demo smoke test.

1. Open Obsidian → `Open folder as vault` → select the `SalesWiki` folder.
2. Open `demo/reports/dashboard-snapshots/sales-today.md` — a populated
   "what to do today" view: hot leads, risky deals, scores and review dates.
3. Click any row to open the underlying card, e.g.
   `demo/demo-vault/wiki/entities/deals/Deal - Atlas Robotics - Pilot.md`.

Everything under `demo/` is synthetic (`synthetic: true`) — explore freely,
nothing can leak.

Want to rerun only the permissioned layer smoke test? It exercises role
contrast, no-leak and the full governance loop against a throwaway vault and
prints PASS/FAIL:

```bash
python3 scripts/demo_dryrun.py
```

## 3. Ask It Questions (3 minutes)

The primary way to ask is a Claude MCP client — **Claude Code, Claude Desktop
or Cowork** — connected to the permissioned MCP gateway. (An optional
Rocket.Chat chat demo for audiences without a Claude client is at the end of
this section.)

### Claude Code / Claude Desktop / Cowork (MCP gateway)

The permissioned MCP gateway answers questions from the demo vault with
citations and role-based access. If you already ran `scripts/first_run.py`,
the virtual environment is ready. Generate config:

```bash
.venv/bin/python scripts/generate_mcp_demo_config.py --personas ae,marketing,curator
```

Paste the generated `mcpServers` block into Claude Code, Claude Desktop,
Cowork or another MCP client, restart the client, then ask:

1. *"What should I do today?"* → `my_day` — leads and deal risks in one digest.
2. *"Brief me on BluePeak Energy."* → `company_brief` — summary with citations;
   what you see depends on your role.
3. *"Which deals are at risk?"* → `deal_risk` — risk factors and next actions.

Demo roles (set via `SALESWIKI_DEMO_ACTOR`): `demo-ethan-ae` (account executive),
`demo-olivia-marketing` (marketing), `demo-claire-hos` (head of sales),
`demo-sophie-curator` (curator/approver), `demo-broad-viewer` (viewer).
Run two entries with different actors side by side to see role contrast:
marketing never sees deal economics, and personal data stays a `restricted://`
handle. The full demo script is
[engineering/permissioned-knowledge-demo-runbook.md](engineering/permissioned-knowledge-demo-runbook.md).

> Demo identity is a server-side environment setting — good for demos and a
> single-operator pilot, not yet real multi-user authentication (SSO is the
> next phase; see `docs/engineering/permissioned-knowledge-sso-design.md`).

### Optional: Rocket.Chat chat demo (no Claude client, no `.venv`)

An optional chat-channel demo of the same permissioned vault — handy for
showing role-based access to an audience without any Claude client: ask in a
channel, switch roles with a command, and watch the same access rules apply.
The default mode imports the in-repo core directly — standard-library only,
no virtualenv.

```bash
export RC_URL="https://your-rocketchat"   # server you can reach
export RC_USER="your-login"               # a normal user account
export RC_PASS="your-password"
export RC_CHANNEL="saleswiki-demo"        # an existing channel, no leading '#'
python3 integrations/rocketchat/bridge.py
```

Then type `demo` in the channel for the full cheat-sheet. Full command list,
prerequisites and the real-MCP mode: `integrations/rocketchat/README.md`.

## 4. Keep It Fresh (1 command)

After any card change, one command validates the vault and rebuilds indexes
and dashboard snapshots:

```bash
python3 scripts/refresh.py          # production data
python3 scripts/refresh.py --demo   # demo data
```

## 5. Where Next

- Add your first real item: drop a free-text request into
  `state/manual-intake.md` — an agent turns it into a proper card
  (see `wiki/processes/manual-intake.md`).
- Working with real sales data? Read the pilot data contract first:
  `wiki/processes/pilot-data-contract.md` — it keeps real data out of this
  repository and out of the demo.
- Day-to-day usage: [USER_GUIDE.en.md](USER_GUIDE.en.md).
- Demo guide: [DEMO.en.md](DEMO.en.md).
- How the permissioned layer works: `docs/engineering/permissioned-knowledge-overview.md`.
