# Contributing

SalesWiki is an Obsidian-first sales knowledge vault plus a permissioned MCP
reference implementation. Contributions should preserve the core contract:
evidence-first Markdown, role-aware reads, cited extract-only answers and
governed changes.

## Local Checks

Run before opening a pull request:

```bash
python3 scripts/public_release_review.py
python3 scripts/health_check.py
python3 -m unittest discover -s tests
python3 scripts/demo_dryrun.py --quiet
```

If you have the MCP SDK installed:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests
```

## Data And Privacy

- Use synthetic data in examples, tests and demos.
- Do not commit real transcripts, emails, CRM exports, customer names, phone
  numbers, credentials, API keys or `.env` files.
- Do not put personal-data bodies in git. Use opaque handles and document the
  intended external store.
- Keep generated indexes rebuildable; update them through scripts, not manual
  edits.

## Change Discipline

- Keep commits focused: docs/release metadata, runtime/deployment, tests and
  feature logic should be separate where practical.
- Update relevant docs when changing behavior.
- Add or update tests for permission, no-leak, approval, worker or answer-format
  changes.
- Fix every `ERROR` and resolve or explain every `WARN` from the health check.

## Public Positioning

Before adding data or generated artifacts, read the
[public repository boundary](docs/REPOSITORY_CONTENTS.en.md). Real pilot,
customer, CRM, contact and transcript data never belongs in this repository.

This project should be described as a reference implementation / starter kit,
not a production SaaS replacement. Real deployments still need identity,
secrets, connector, backup and incident-response decisions.
