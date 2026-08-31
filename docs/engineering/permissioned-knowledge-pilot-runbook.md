# Lead-Priority Pilot Runbook

The one thing no agent or test can do for this project: prove the product on
**real data**. This runbook operationalizes the recommended adoption wedge —
`lead_priority` for sales — as a four-week, single-operator pilot with one
real inflow path and a staleness measure. Everything here composes existing
contracts; read
[`wiki/processes/pilot-data-contract.md`](../../wiki/processes/pilot-data-contract.md)
first — it is the boundary this runbook runs inside.

## Hypothesis and measures

**Hypothesis (I1):** a rep gets a faster, trustworthy "which leads do I touch
today and why" answer from SalesWiki than from HubSpot/Obsidian directly.

Suggested targets — confirm or adjust at kickoff, then do not move them
mid-pilot:

| Measure | How it is taken | Target at week 4 |
| --- | --- | --- |
| Usage | questions asked against the pilot vault, per week (pilot log) | ≥ 3/week sustained |
| Usefulness | operator/rep rating per answer: `useful` / `neutral` / `wrong` | ≥ 70% `useful` |
| Trust loop | wrong/stale data caught via `flag_stale_or_wrong` → approve → worker apply | ≥ 1 full loop on real data |
| Staleness (I4) | % of pilot lead cards past their cadence window (see Step 5) | < 20% |
| Speed | occasional side-by-side: same question answered from HubSpot manually | SalesWiki subjectively faster |

**Kill criteria:** usage falls to zero for two consecutive weeks, or the rep
rates the answers mostly `wrong`, or staleness cannot be held under the target
with the weekly inflow — stop, record why in the architecture's Product Risks,
and exit per the pilot contract (delete or keep the vault; nothing in the
platform repo needs cleanup).

## Preconditions (go/no-go)

- [ ] `wiki/processes/pilot-data-contract.md` read; pilot vault initialized
      **outside this repository** (e.g. `~/SalesWiki-pilot/`), `git init`, **no remote**.
- [ ] Pilot repo `.gitignore` covers `runtime/` and `*.approval_key`.
- [ ] ADR-0018 resolved for this pilot: personal-data bodies are **not** git-tracked —
      contacts stay reference handles; raw exports live outside the vault or in an
      erasable store.
- [ ] Single-operator model accepted: the vault lives on the curator's machine only;
      reps get answers relayed/supervised, not the folder (honest access model, pre-SSO).
- [ ] The demo path works end to end on this machine (`docs/QUICKSTART.en.md`),
      so pilot issues are pilot issues, not setup issues.

## Step 1 — Seed real lead cards (day 0, ~2h)

Pick **10–20 leads the rep actually cares about this month**, across the two
segments from
[`wiki/processes/sales-team-feedback-requirements.md`](../../wiki/processes/sales-team-feedback-requirements.md):

- `pipeline_segment: qualification` / MQL — the weekly-cadence group;
- `pipeline_segment: outside-pipeline` — promising, monthly/trigger cadence.

For each lead (and its company, if the card does not exist yet):

```bash
python3 scripts/new_entity.py --type company --name "Acme GmbH" \
  --natural-key acme.de --vault-root ~/SalesWiki-pilot --ledger ~/SalesWiki-pilot/state/id-ledger.jsonl
python3 scripts/new_entity.py --type lead --name "Acme GmbH - Inbound Demo Request" \
  --natural-key hubspot:12345 --vault-root ~/SalesWiki-pilot --ledger ~/SalesWiki-pilot/state/id-ledger.jsonl
```

Then fill the card body/frontmatter (template: `wiki/entities/leads/_template.md`):

- `dataset: pilot`, an access label (`sales-confidential` default), `owner:`
  (the rep — this drives the `assigned` ABAC), `company:` link.
- Score via the `saleswiki-lead-scoring` skill: `score`, `score_band`,
  `scored_at`, `next_review`, plus the why-now and next action in the body —
  these are exactly what `lead_priority` extracts and cites.
- Contact details stay handles (`restricted://…` / CRM link), never full PII bodies.

Rebuild derived data for the pilot roots (repeat after every card change):

```bash
python3 scripts/build_indexes.py --source-root ~/SalesWiki-pilot \
  --output-root ~/SalesWiki-pilot/indexes --no-update-state
```

## Step 2 — Wire the query surface (once)

The gateway refuses non-demo vaults by default
([`saleswiki_mcp/vault_guard.py`](../../saleswiki_mcp/vault_guard.py)):
fixture identity is not authentication. Running it against the pilot vault is
an **explicit accepted risk**, sound only under the single-operator model
above — one human, one machine, no shared channel:

```json
{
  "mcpServers": {
    "saleswiki-pilot-ae": {
      "command": "/path/to/SalesWiki/.venv/bin/python",
      "args": ["-m", "saleswiki_mcp.server"],
      "env": {
        "SALESWIKI_DEMO_ACTOR": "demo-ivan-ae",
        "SALESWIKI_VAULT_ROOT": "/path/to/SalesWiki-pilot",
        "SALESWIKI_RUNTIME_DIR": "/path/to/SalesWiki-pilot/runtime",
        "SALESWIKI_ALLOW_PROD_VAULT": "1",
        "PYTHONPATH": "/path/to/SalesWiki"
      }
    }
  }
}
```

Notes:

- Map fixture actors to real people 1:1 for the pilot (e.g. `demo-ivan-ae` = the
  rep, `demo-marina-curator` = you) and set `owner:` on lead cards accordingly;
  add a second server entry per extra role when needed.
- The **Rocket.Chat bridge stays demo-only**: channel members self-assert roles,
  which must never happen over real data (auth-review H5). Pre-SSO, pilot access
  is Claude Desktop/Code on the curator's machine.
- Approved proposals are applied by the single writer, pointed at the same roots
  via the same env vars:
  `SALESWIKI_VAULT_ROOT=~/SalesWiki-pilot SALESWIKI_RUNTIME_DIR=~/SalesWiki-pilot/runtime python3 -m saleswiki_mcp.worker`
  (see [`permissioned-knowledge-overview.md`](permissioned-knowledge-overview.md)).

## Step 3 — One real inflow path (weekly, ~30 min)

Mitigates I4 (no inflow → silent decay). The cheapest honest path:

1. Every Monday, export the lead list view from HubSpot (CSV) for the pilot leads.
2. Store the export **outside the vault** (or delete after processing); it is
   reference material, not vault content.
3. For each changed lead: update the card (`crm_stage`, `last_touched`, body
   note with the trigger), re-run scoring if factors moved, bump `updated:`.
4. New promising lead → seed it via Step 1's chokepoint. Dead lead → archive per
   [`wiki/processes/deletion-and-archiving.md`](../../wiki/processes/deletion-and-archiving.md).
5. Rebuild indexes (Step 1's command) and add an inflow line to the pilot log.

## Step 4 — The daily loop

The rep (with or via the curator) asks, at minimum:

- *"What should I do today?"* → `my_day`
- *"Which leads first?"* / per-company → `lead_priority`

For every answer, one log line: date, question, tool, rating
(`useful`/`neutral`/`wrong`), and — when `wrong` — a `flag_stale_or_wrong`
proposal so the correction rides the governed loop instead of an untracked edit.

## Step 5 — Staleness measure (weekly)

A pilot lead card is **stale** when `updated:` is older than its cadence window:
**7 days** for `qualification`/MQL, **30 days** for `outside-pipeline` (aligned
with [`wiki/processes/freshness-and-decay.md`](../../wiki/processes/freshness-and-decay.md)).
Take the number weekly, after the inflow pass:

```bash
python3 - <<'EOF'
from datetime import date, timedelta
from pathlib import Path
import re
root, today = Path.home() / "SalesWiki-pilot", date.today()
windows = {"qualification": 7, "mql": 7, "outside-pipeline": 30}
total = stale = 0
for card in (root / "wiki" / "entities" / "leads").rglob("*.md"):
    text = card.read_text(encoding="utf-8")
    seg = re.search(r"^pipeline_segment:\s*(\S+)", text, re.M)
    upd = re.search(r"^updated:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if card.name.startswith("_"):
        continue
    total += 1
    limit = windows.get(seg.group(1) if seg else "", 7)
    if not upd or date.fromisoformat(upd.group(1)) < today - timedelta(days=limit):
        stale += 1
print(f"{stale}/{total} stale ({stale * 100 // max(total, 1)}%)")
EOF
```

## Weekly checkpoint (pilot log)

Keep one table in the pilot vault (`~/SalesWiki-pilot/state/pilot-log.md`):

| Week | Lead cards | % stale | Questions | Useful | Wrong | Flags→applied | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Exit (end of week 4)

- **Go:** hypothesis held → widen deliberately: confirm `lead_priority` as the
  sales wedge in the architecture's Open Decisions, start the marketing wedge
  (`content_opportunities`), and treat promotion of pilot data to production as a
  reviewed import ([`wiki/processes/external-vault-import.md`](../../wiki/processes/external-vault-import.md)).
  Shared multi-user access remains gated on SSO
  ([`permissioned-knowledge-sso-design.md`](permissioned-knowledge-sso-design.md)).
- **No-go:** record the observed reason under Product Risks in
  [`permissioned-knowledge-architecture.md`](permissioned-knowledge-architecture.md)
  (that section exists precisely so failures are not assumed away) and exit per
  the pilot contract.

## Out of scope for this pilot

No shared/multi-user access (SSO gate), no automated connectors (HubSpot API,
Drive/Meet, Slack — all `status: planned`), no Rocket.Chat over real data, no
LinkedIn automation. One wedge, one inflow path, four weeks.
