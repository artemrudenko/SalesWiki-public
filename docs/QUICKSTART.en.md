# Run SalesWiki locally

The Workbench has two modes: a browser-only synthetic preview and a local path
that calls the permissioned Python service.

## Browser preview

```bash
cd apps/workbench
npm ci
npm run dev
```

Open the local URL printed by Vite. This mode uses built-in synthetic data.

## Workbench with the permissioned service

In a second terminal from the repository root, install the MCP SDK and start
the local demo service:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
SALESWIKI_DEMO_ACTOR=demo-sophie-curator \
  .venv/bin/python -m integrations.workbench.server \
  --config config/workbench-demo.example.toml
```

Then start the interface with the service endpoint enabled:

```bash
cd apps/workbench
VITE_SALESWIKI_GRAPH_ENDPOINT=/api/v1/entity-graph npm run dev -- --host localhost --port 4173
```

To exercise the complete role-access, review, apply, audit, and rollback path:

```bash
.venv/bin/python scripts/demo_dryrun.py
```

All actors and records are synthetic. The service accepts the demo vault only;
the fixture persona selector is not authentication. Do not connect this demo to
customer systems or store real customer data in this repository.
