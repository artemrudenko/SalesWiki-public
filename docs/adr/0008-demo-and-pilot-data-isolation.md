---
status: Accepted
date: 2026-06-24
deciders: SalesWiki maintainers
---

# ADR-0008: Demo vault separated from production; pilot data lives outside the repo

## Status

Accepted — backfilled record of a decision established earlier in the project (see Context).

## Context

SalesWiki is a shareable platform repository (code, schemas, templates, process docs), but it must also support sales/marketing demos and a first real-data pilot. Synthetic demo cards must never be mistaken for real data or used in CRM/reporting, and real pilot data (accounts, leads, deals, transcripts) must have no path to leak into this repository, the demo dataset, or a remote it must not reach. The project needed three strictly separated contours — Demo, Platform, Pilot — with machine-enforced boundaries. This was established in `wiki/processes/demo-vault.md` and `wiki/processes/pilot-data-contract.md`, and recorded in the README "Принятые решения" list.

## Decision

We separate the three contours and enforce the boundary in `scripts/health_check.py`. Demo data lives under `demo/` inside this repo, every demo card carries `dataset: demo`, `synthetic: true` and an id prefixed `demo-`, and it may be regenerated or deleted without approval (`scripts/generate_demo_vault.py --reset`); `check_demo_boundary` / `check_real_card_data_quality` fail if a demo/synthetic card appears in production `wiki/entities/`. Real pilot data uses `dataset: pilot` and lives in a separate vault **outside this repository** (e.g. `~/SalesWiki-pilot/`); `check_pilot_boundary` fails the build if a `pilot/` directory or any `dataset: pilot` file appears in the repo, and `.gitignore` blocks an accidental local `pilot/` folder. All platform scripts accept explicit `--source-root`/`--output-root` (and the gateway reads `SALESWIKI_VAULT_ROOT`) so code stays here and data stays there.

## Consequences

**Positive**
- Real pilot data cannot be committed here; the health check fails the build if it appears.
- Demo data is safe to regenerate/delete and is unmistakably synthetic, so it can never be passed off as real.
- The platform repo stays shareable while still driving demo and pilot vaults via explicit roots.

**Negative / trade-offs**
- The pilot vault needs its own git history, backups and (until SSO) lives on the curator's machine only, so team members get value via digests, not folder access.
- Running checks/indexes/snapshots across contours means passing explicit root flags, which is easy to forget.
- Promoting a successful pilot to production is a reviewed import, not a copy-paste.

## Alternatives considered

- **One vault with a `dataset` flag separating demo/pilot/production** — rejected: file-level access means anyone who can open the folder reads everything; a flag does not stop real data leaking into the shared repo.
- **Demo data inside `wiki/entities/`** — rejected: risks synthetic cards polluting production indexes and being used in real reporting; the boundary check forbids it.
- **Pilot data committed to a private branch/remote of this repo** — rejected: still places real data in the platform repo's history; the pilot contract keeps it in a separate vault with no remote by default.

## References

- [[demo-vault]] — `wiki/processes/demo-vault.md`
- [[pilot-data-contract]] — `wiki/processes/pilot-data-contract.md`
- `scripts/health_check.py` (check_demo_boundary, check_pilot_boundary, check_real_card_data_quality)
- `scripts/generate_demo_vault.py`
- `README.md` (## Принятые решения)
