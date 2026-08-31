# SalesWiki Demo Workspace

This folder contains isolated synthetic demo data for sales/marketing presentations.

- `demo-vault/` opens as a separate Obsidian vault.
- `indexes/` contains generated demo indexes.
- `reports/dashboard-snapshots/` contains generated demo dashboard snapshots.
- `reports/digests/` contains generated role digests (`my_day` / `pipeline_risk_digest`) in delivery format — what each persona would receive by Slack/email.
- `permissioned/` is the isolated sub-vault for the permissioned-knowledge MVP (role-aware boundaries). For the full end-to-end demo (actors, structure, before/during/after commands, diagrams) follow `docs/engineering/permissioned-knowledge-demo.md`; its transient runtime lives in `demo/runtime/`.

Regenerate:

```bash
python3 scripts/generate_demo_vault.py --reset
python3 scripts/refresh.py --demo
python3 scripts/generate_demo_digests.py
```

All demo cards are synthetic and may be deleted or regenerated without approval.
