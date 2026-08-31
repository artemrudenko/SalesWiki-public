# Reports

Generated and curated reports for SalesWiki users.

`reports/dashboard-snapshots/` contains Markdown snapshots generated from derived indexes by:

```bash
python3 scripts/build_dashboard_snapshots.py
```

Generated snapshots are safe to rebuild. Do not put raw personal data in snapshots.

Public snapshots do not include staged event-research pilot artifacts. Run new
event pilots in a separate working folder first, then promote only approved,
cited outputs into the vault.
