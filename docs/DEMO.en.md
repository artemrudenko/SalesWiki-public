# SalesWiki Demo

This is the shortest guided path for evaluating SalesWiki from a fresh clone.
Everything in the demo is synthetic; no real customer data is required.

## Fastest Path

Run one command from the repository root:

```bash
python3 scripts/first_run.py
```

Expected result:

```text
SalesWiki first run completed.
```

That command creates `.venv`, installs the MCP dependency, checks the public
release guardrails, validates the vault and runs the permissioned demo smoke
test.

Docker alternative:

```bash
docker compose run --rm first-run
```

## What To Open

After the first run, open the repository root in Obsidian and start here:

1. `demo/reports/dashboard-snapshots/sales-today.md` — the sales "what to do
   today" view.
2. `demo/reports/dashboard-snapshots/deal-risk.md` — risky deals and why they
   need attention.
3. `demo/reports/digests/my-day-ae.md` — an account-executive daily digest.
4. `demo/demo-vault/wiki/entities/deals/Deal - Atlas Robotics - Pilot.md` — a
   concrete synthetic deal card.

## Ask Questions Through MCP

Generate ready-to-paste MCP client config:

```bash
.venv/bin/python scripts/generate_mcp_demo_config.py --personas ae,marketing,curator
```

Paste the generated `mcpServers` block into Claude Desktop, Claude Code, Cowork
or another MCP client, then restart the client.

Try:

1. "What should I do today?"
2. "Brief me on BluePeak Energy."
3. "Which deals are at risk?"
4. Ask the same question as `ae` and `marketing` to see role-based filtering.

The demo actors are fixtures. They are useful for demos and single-operator
pilots, not production multi-user authentication.

## Optional Rocket.Chat Demo

Rocket.Chat is optional. Use it only when you already have a reachable
Rocket.Chat server, a normal user account and an existing channel:

```bash
export RC_URL="https://your-rocketchat"
export RC_USER="your-login"
export RC_PASS="your-password"
export RC_CHANNEL="saleswiki-demo"
python3 integrations/rocketchat/bridge.py
```

Then type `demo` in the channel. Full details:
`integrations/rocketchat/README.md`.

## Reset Demo State

```bash
rm -rf demo/mcp-demo demo/runtime
python3 scripts/demo_dryrun.py --quiet
```

## What This Demo Proves

- The vault opens as plain Markdown in Obsidian.
- The generated indexes and dashboard snapshots are reproducible.
- The MCP gateway returns cited answer envelopes instead of free-form guesses.
- Role-aware access hides sales-confidential and personal-data details.
- Governed changes go through proposal, approval and worker apply.

## What It Does Not Prove Yet

- Production SSO.
- Hosted multi-user operations.
- Real CRM / Drive / Meet sync.
- External personal-data storage.
- Compliance-grade backup, monitoring and incident response.
