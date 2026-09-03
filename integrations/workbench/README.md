# Knowledge Workbench BFF (demo only)

This optional loopback service connects the local Knowledge Workbench to the
real `saleswiki.entity_graph` MCP stdio tool and the governed proposal-review
tools. It exists to verify the complete browser → MCP → policy path with
synthetic data.

It is not a production gateway:

- a configured synthetic fixture actor starts the local demo; optional demo
  persona switching is an opaque server-side session, never a browser role;
- the browser cannot send actor, role, tool name, vault or credentials;
- only demo/synthetic vaults are accepted;
- read endpoints and the two allowlisted proposal decisions are no-store,
  bounded and response-validated;
- approval is not a card write: it only records the existing governed proposal
  decision for the separate worker;
- the account brief and update-proposal endpoints invoke only the fixed,
  role-aware `company_brief` and `flag_stale_or_wrong` MCP tools;
- CORS/origin checks are not authentication;
- there is no TLS, SSO or per-request identity.

Run it with the curator demo profile to inspect and decide proposals:

```bash
export SALESWIKI_DEMO_ACTOR=demo-sophie-curator
.venv/bin/python -m integrations.workbench.server \
  --config config/workbench-demo.example.toml
```

Start the UI separately with the same-origin development proxy:

```bash
cd prototypes/knowledge-workbench
VITE_SALESWIKI_GRAPH_ENDPOINT=/api/v1/entity-graph \
  npm run dev -- --host 0.0.0.0 --port 4173 --strictPort
```

See [`docs/DEPLOYMENT.en.md`](../../docs/DEPLOYMENT.en.md) for the full local
path and [`docs/engineering/permissioned-knowledge-sso-design.md`](../../docs/engineering/permissioned-knowledge-sso-design.md)
for the hosted OAuth replacement.

When `allow_fixture_persona_switching = true` is set in the demo config, the
top bar can switch among listed **synthetic** people. The browser submits only
an allowlisted fixture id; the BFF owns the role mapping and creates an opaque,
short-lived `HttpOnly` session. This is a presentation feature for the
synthetic vault, not a login system. In a real shared deployment, a verified
SSO identity replaces this selector and no role switch is shown.

Use `demo-raj-revops` to inspect the queue without decision permission. The
full flow and request boundary are documented in
[`docs/engineering/workbench-review-inbox.md`](../../docs/engineering/workbench-review-inbox.md).
