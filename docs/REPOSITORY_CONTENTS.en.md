# Public Repository Boundary

This repository is the public, reproducible **platform contour** of SalesWiki.
It must be useful from a fresh clone without containing customer or operator
data. The boundary is deliberately stricter than “do not commit passwords.”

## What Belongs Here

- application code, tests, schemas and connector contracts;
- Markdown templates and the sales/marketing operating model;
- public architecture, deployment, security and contributor documentation;
- synthetic demo cards marked `dataset: demo` and `synthetic: true`;
- deterministic demo reports and generated indexes needed to inspect the example;
- editable diagram sources and rendered publication assets;
- empty raw-source directories represented by their README files;
- example configuration files whose values are visibly fake.

Generated indexes are committed only when they are part of the inspectable demo
or public vault snapshot. They remain derived artifacts: rebuild them from the
Markdown source instead of editing them manually.

## What Must Stay Out

- real customer, lead, contact, deal, CRM, call or meeting data;
- a real pilot vault or any file marked `dataset: pilot`;
- credentials, tokens, approval-signing keys and populated environment files;
- runtime proposals, grants, audit logs, dead-letter queues, locks and uploads;
- local Obsidian state, virtual environments, tool caches and editor settings;
- test coverage output, local databases, debug logs and dependency directories;
- temporary import packages or connector downloads containing source material.
- machine-local `config/runtime.toml`; commit only `runtime.example.toml`.

Real pilot data belongs in a separate, private, access-controlled vault outside
this checkout. Point the gateway at it with `SALESWIKI_VAULT_ROOT`; do not add it
as a subdirectory or Git submodule of the public repository.

## Publication Gate

Before pushing a public snapshot, run:

```bash
python3 scripts/public_release_review.py
python3 scripts/health_check.py
.venv/bin/python -m unittest discover -s tests
python3 scripts/demo_dryrun.py --quiet
```

Also inspect ignored files with `git status --ignored --short` and the staged
snapshot with `git diff --cached`. The automated review detects tracked private
paths and common credential shapes; it cannot prove that prose or synthetic-looking
fixtures contain no confidential business context.

## Private-to-Public Release Sync

Keep the working repository private and authoritative. Do not mirror its Git
history to the public project. For each public release, create a clean snapshot:

```bash
python3 scripts/export_public_snapshot.py --output ../SalesWiki-public
cd ../SalesWiki-public
python3 scripts/health_check.py
python3 scripts/demo_dryrun.py
git init
git add .
git commit -m "Release SalesWiki public preview"
```

Push that new history to the separate public repository only after reviewing
the snapshot. Changes or issue fixes from the public project are always brought
back as a reviewed change in the private source repository, never by merging
public history inward.

## Forks And Extensions

Keep product extensions in the public repository only when they remain generic
and testable without private data. Put customer-specific policy overlays,
identity mappings, connector credentials and retention rules in the deployment
environment or a private companion repository.
