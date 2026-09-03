# SalesWiki Deployment

SalesWiki has two practical deployment modes today:

1. **Local demo / local pilot** — recommended for the public starter kit.
2. **Docker demo runtime** — useful for repeatable checks and MCP stdio demos.

It is not yet a production multi-user service. Real production deployment still
requires the shared identity work described in
`docs/engineering/permissioned-knowledge-sso-design.md`.

## Local Demo

Use this path to inspect the vault, run the synthetic demo and connect a local
MCP client.

```bash
git clone <repo-url> SalesWiki
cd SalesWiki
python3 scripts/first_run.py
```

Open the repository root in Obsidian to browse the Markdown vault. Start with
`README.md`, `docs/QUICKSTART.en.md` and `demo/reports/dashboard-snapshots/`.

## Local MCP Gateway

The MCP gateway uses stdio. It is normally launched by Claude Code, Claude
Desktop, Cowork or another MCP client, not as a web server.

Example Claude Desktop-style entry:

```json
{
  "mcpServers": {
    "saleswiki-ae": {
      "command": "/absolute/path/to/SalesWiki/.venv/bin/python",
      "args": ["-m", "saleswiki_mcp.server"],
      "env": {
        "SALESWIKI_DEMO_ACTOR": "demo-ethan-ae",
        "PYTHONPATH": "/absolute/path/to/SalesWiki"
      }
    }
  }
}
```

Demo actors are listed in `docs/QUICKSTART.en.md`. Fixture identity is safe for
synthetic demos and single-operator pilots only.

## Knowledge Workbench Through The Real MCP Tool

The optional local Workbench BFF lets the browser exercise the real
`saleswiki.entity_graph`, daily-priority and governed proposal-review MCP tools
without putting an actor, role, vault path or MCP credential in JavaScript. It
is deliberately a **synthetic demo path**, not SSO or production hosting.

Install the optional MCP SDK in `.venv`, then start the loopback BFF:

```bash
export SALESWIKI_DEMO_ACTOR=demo-sophie-curator
.venv/bin/python -m integrations.workbench.server \
  --config config/workbench-demo.example.toml
```

In another terminal, start the UI with its same-origin development proxy:

```bash
cd prototypes/knowledge-workbench
VITE_SALESWIKI_GRAPH_ENDPOINT=/api/v1/entity-graph \
  npm run dev -- --host 0.0.0.0 --port 4173 --strictPort
```

The UI shows the server-resolved synthetic person and role whenever this
transport is active. With `allow_fixture_persona_switching = true` in the demo
configuration, a facilitator can select another listed synthetic person in the
top bar without restarting the BFF. The browser submits only an allowlisted
fixture ID; it cannot choose a role or permissions. The BFF binds to
`127.0.0.1:8787` by default, caps concurrency, applies a hard MCP timeout,
validates its response contracts and returns
`Cache-Control: no-store`. The Review view receives the server-derived
`can_decide` flag; approve/reject still record an append-only proposal decision
and never write a card directly. Its health endpoint is
`http://127.0.0.1:8787/health` and exposes no actor or vault information.

This switch is a synthetic-demo convenience, not shared-user authentication.
Real deployments must replace it with per-request OAuth/SSO identity and do
not expose a role picker.

The Workbench displays its shared `Review` entry point only when the
server-owned session capability `can_review` is true. This is a usability hint,
not an authorization substitute: the BFF and MCP policy independently deny a
non-reviewer queue request. A future `My requests` screen must use a dedicated
server endpoint that returns only the authenticated actor's proposals; it must
never filter a shared queue in the browser. See
[`ADR-0026`](adr/0026-workbench-review-capability-hint.md).

The BFF refuses non-loopback binding. To show the synthetic demo on a local
network, expose the UI development server only; its same-origin proxy keeps the
BFF and its session cookie on the presentation machine.

Do not point this bridge at a real, pilot or unmarked vault. It independently
requires demo/synthetic markers even if the generic production-vault override
is present. Shared real-data use still requires hosted Streamable HTTP MCP,
per-request OAuth identity, HTTPS, rate limits and monitoring.

## Runtime Configuration

The integration runtime has a typed TOML profile:

```bash
cp config/runtime.example.toml config/runtime.toml
export SALESWIKI_CONFIG=config/runtime.toml

python3 -m saleswiki_runtime config validate
python3 -m saleswiki_runtime config show --redacted
python3 -m saleswiki_runtime doctor
```

`config/runtime.toml` is ignored by Git and Docker. It contains deployment
choices and references to environment variables, never credentials themselves.
The existing Rocket.Chat `RC_*` variables remain temporarily supported when
`SALESWIKI_CONFIG` is absent, with a deprecation warning.

## Audit checkpoints for a private pilot

The JSONL audit log is hash chained, which exposes changes to its recorded
history. A clean deletion of the newest lines needs a separate checkpoint to be
noticed. For a private pilot, keep the checkpoint in a protected directory that
is not mounted into the gateway or worker runtime, and keep the HMAC key in a
secret manager or deployment-only environment variable.

Bootstrap the first checkpoint after a clean verification:

```bash
export SALESWIKI_AUDIT_ANCHOR_KEY='<deployment-only secret>'
python3 scripts/audit_anchor.py create \
  --audit /srv/saleswiki-runtime/audit.jsonl \
  --anchor /srv/saleswiki-audit-checkpoints/audit.anchor.json
```

Run verification on a schedule. Only advance a checkpoint after verification;
the command refuses to replace a checkpoint that does not verify.

```bash
python3 scripts/audit_anchor.py verify \
  --audit /srv/saleswiki-runtime/audit.jsonl \
  --anchor /srv/saleswiki-audit-checkpoints/audit.anchor.json
python3 scripts/audit_anchor.py advance \
  --audit /srv/saleswiki-runtime/audit.jsonl \
  --anchor /srv/saleswiki-audit-checkpoints/audit.anchor.json
```

Treat a failed verification as an incident: preserve both files, restrict write
access and investigate before creating any new checkpoint. The checkpoint is a
low-infrastructure pilot control, not a substitute for an immutable remote log,
SSO identity, retention policy, backups or monitoring. See
[`ADR-0031`](adr/0031-signed-audit-checkpoints.md).

## Docker Checks

Build once:

```bash
docker compose build
```

The public Compose services use a read-only root filesystem and a temporary
`/tmp`. The MCP demo receives one writable named volume for proposal and audit
runtime state. This hardens the preview, but it is not the production gateway /
worker mount topology described below.

Run the complete public demo setup/check path:

```bash
docker compose run --rm first-run
```

Or run checks individually.

Run the public-release review:

```bash
docker compose run --rm check
```

Run the core health check:

```bash
docker compose run --rm health
```

Run tests in an isolated environment with optional LLM features disabled:

```bash
docker compose run --rm test
```

Run the permissioned demo smoke test:

```bash
docker compose run --rm demo
```

## Docker MCP Stdio Demo

The `mcp-ae` service starts the MCP stdio server as the demo account executive:

```bash
docker compose run --rm mcp-ae
```

This is mainly useful for MCP clients or manual protocol experiments that can
attach to container stdio. It is not an HTTP endpoint.

Runtime state is stored in the `saleswiki-runtime` Docker volume so proposal and
audit demo state can survive across container runs. Delete it when you need a
fresh demo:

```bash
docker compose down -v
```

## Real Data Rules

- Do not put real customer or personal data in this public repository.
- Keep real pilot vaults outside the repo, private and access-controlled.
- Mount private vaults read-only for the gateway unless you are running the
  single-writer worker.
- Store connector/OIDC/chat/LLM credentials in environment variables or a
  secret manager.
- Do not mount `.env`, approval keys or raw personal-data bodies into a public
  workspace.

## Production Gap

Before using SalesWiki as a shared production service, finish:

- per-request SSO / broker-issued identity;
- connector credential storage;
- backup and restore drills;
- hosted logging/monitoring/rate limits;
- incident response;
- external erasable personal-data storage.

The local Workbench BFF does not close these gaps; it validates the UI-to-MCP
contract while keeping fixture identity visibly demo-only.
