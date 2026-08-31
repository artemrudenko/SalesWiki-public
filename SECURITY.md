# Security Policy

SalesWiki is a public reference implementation and starter kit, not a hosted
production service. Treat this repository as public even when you run it
privately.

## Supported Scope

The public repository supports:

- synthetic demo data under `demo/`;
- local health checks, indexes and dashboard snapshots;
- the permissioned MCP demo gateway with fixture identity;
- governed proposal/approval/worker flows on synthetic or explicitly staged
  data.

The public repository does **not** provide production-ready SSO, hosted incident
response, connector credential management, backup/restore drills or an erasable
personal-data store.

## Data Rules

- Do not commit real customer data, call transcripts, emails, CRM exports,
  contact details, credentials, API keys or access tokens.
- Keep real pilot data in a private, out-of-repository vault. See
  `wiki/processes/pilot-data-contract.md`.
- Keep personal-data bodies out of git. Use governed handles such as
  `restricted://...` until an external erasable store exists.
- Store secrets in environment variables or a secret manager, never in Markdown,
  JSON, `.env`, shell history snippets or committed config.

## Reporting A Vulnerability

If you find a security issue, do not open a public issue with exploit details or
real data. Open a minimal private report through the repository owner's preferred
contact path, or create a public issue that says only that a private security
report is needed.

Include:

- affected file or feature;
- minimal reproduction using synthetic data;
- expected vs actual access boundary;
- whether any secret, customer data or personal data was exposed.

## Before Publishing A Fork

Run:

```bash
python3 scripts/public_release_review.py
python3 scripts/health_check.py
python3 -m unittest discover -s tests
python3 scripts/demo_dryrun.py --quiet
```

The public-release review is heuristic. It does not replace a human review of
git history and any private deployment files.
