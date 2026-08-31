# Pilot Data Contract

The pilot contour is where the first real sales/marketing data lives during a
controlled pilot. Its single purpose: let the team work with real accounts,
leads, deals and call insights **without any path for that data to leak** into
this repository, the demo dataset, or any remote it must not reach.

Three contours, strictly separated:

| Contour | Contents | Where it lives |
| --- | --- | --- |
| Demo | Synthetic cards (`dataset: demo`, `synthetic: true`) | `demo/` in this repository — see [[demo-vault]] |
| Platform | Code, schemas, templates, process docs | This repository (shareable) |
| Pilot | Real team data (`dataset: pilot`) | A separate vault **outside this repository** |

## Location

Recommended: `~/SalesWiki-pilot/` (or another path outside this repo), mirroring
the production layout:

```text
~/SalesWiki-pilot/
  wiki/entities/
  raw/
  tracking/
  state/
  indexes/
  reports/
```

Hard rules, enforced by `scripts/health_check.py` (`check_pilot_boundary`):

- No `pilot/` directory may exist inside this repository.
- No file with `dataset: pilot` may exist inside this repository.
- `.gitignore` additionally blocks an accidental local `pilot/` folder.

## Data Rules

- Every pilot card uses `dataset: pilot` in frontmatter.
- Access labels are mandatory on every card (`internal`, `sales-confidential`,
  `personal-data`, `legal-review`); when unsure, pick the stricter label.
- Entity ids are minted through the normal chokepoint
  (`scripts/new_entity.py` per [[identifier-strategy]]); the id ledger lives in
  the pilot vault, not here.
- All production governance applies: `Controlled Profile` protection,
  source tracking, dedupe, freshness — pilot data is real data.

## Reference-Only For Sensitive Sources

The most sensitive material never enters the pilot vault as full text:

- Call transcripts, CRM exports, contact lists: store a **reference**
  (Drive path or system link) under `raw/`, plus extracted, reviewed insights.
- Anything with personal data passes the `privacy-redaction-reviewer` flow
  before it appears in a card body; names/contacts of people outside the team
  stay as restricted handles, mirroring the permissioned gateway behavior.

## Git Rules

- The pilot vault is its own git repository (for history and recovery), with
  **no remote** at the start of the pilot. Adding a remote requires an explicit
  decision: private repository, access reviewed, and an entry in the pilot
  vault's `state/` log.
- **Personal-data bodies must NOT be git-tracked** (ADR-0018): git history makes
  erasure impossible, so a pilot vault that would hold personal-data bodies must
  keep them in an external erasable store (handles only in the vault), or not use
  git-history as the recovery mechanism for that data. A handles-only vault may
  remain a git repo. Resolve this **before** onboarding real personal data.
- **Gitignore the runtime.** The MCP runtime (`runtime/audit.jsonl`,
  `runtime/proposals.jsonl`, `.approval_key`) is operational state, not vault
  content — add a `.gitignore` in the pilot repo for `runtime/` and `*.approval_key`
  so per-query audit logs and the signing key are never committed (the platform
  repo already gitignores its own `demo/runtime/`).
- Never commit pilot files into this (platform) repository. The health check
  fails the build if pilot-marked content appears here.
- Backups: encrypted disk or the team's approved private storage only.

## Working With The Pilot Vault

All platform scripts accept explicit roots, so the code stays here and the data
stays there:

```bash
python3 scripts/health_check.py                       # platform integrity
python3 scripts/build_indexes.py \
  --source-root ~/SalesWiki-pilot --output-root ~/SalesWiki-pilot/indexes --no-update-state
python3 scripts/build_dashboard_snapshots.py \
  --index-root ~/SalesWiki-pilot/indexes --output-root ~/SalesWiki-pilot/reports/dashboard-snapshots
```

The permissioned MCP gateway points at the pilot vault via environment:

```bash
SALESWIKI_VAULT_ROOT=~/SalesWiki-pilot SALESWIKI_RUNTIME_DIR=~/SalesWiki-pilot/runtime \
  .venv/bin/python -m saleswiki_mcp.server
```

## Honest Access Model (Pilot Stage)

The gateway enforces role-based answers, but file-level access is the real
boundary: whoever can open the pilot folder can read everything in it.
Therefore, until SSO ships (see
`docs/engineering/permissioned-knowledge-sso-design.md`):

- The pilot vault lives on the curator's machine only.
- Team members contribute through `state/manual-intake.md` Quick Drop entries
  (relayed via the curator) and receive value through digests and answers —
  they do not get the folder.
- Moving to shared multi-user access is a separate go/no-go decision gated on
  SSO and a deployment boundary, not a default next step.

## Exit Paths

- Pilot succeeds → its vault becomes production data; promotion is a reviewed
  import (see [[external-vault-import]]), not a copy-paste.
- Pilot is abandoned → delete the pilot vault and backups; nothing in this
  repository needs cleanup, because nothing pilot-related is allowed here.

## See Also

- `docs/engineering/permissioned-knowledge-pilot-runbook.md` — the executable
  four-week `lead_priority` pilot that runs inside this contract.
- [[demo-vault]] — the synthetic presentation contour.
- [[permission-boundary-blueprint]] — boundary thinking before sensitive ingest.
- [[access-and-redaction-policy]] — labels and redaction rules.
- `docs/QUICKSTART.en.md` / `docs/QUICKSTART.ru.md` — the 5-minute first run.
