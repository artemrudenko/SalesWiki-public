# SalesWiki

Sales and marketing teams share account knowledge, but they often need different
answers from it. SalesWiki explores how one evidence base can support those
decisions while keeping access, freshness, and review visible.

**[Open the Workbench demo](https://knowledge-workbench-seven.vercel.app/)**

This repository includes both the Workbench interface and the permissioned
knowledge service behind the concept. The implementation demonstrates:

- access checks before information is returned, using role and account context;
- answers grounded in cited records, with freshness and missing context shown;
- stale information as a cue to review, not proof of why it became stale;
- proposed changes routed for human approval before a separate worker applies
  them, with an audit trail and rollback path;
- synthetic sales and marketing scenarios that show the same account through
  different role-specific lenses.

## Run the demo

For the browser interface, see the [quick start](docs/QUICKSTART.en.md). To
exercise the permissioned service and its governed update path, run:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/demo_dryrun.py
```

The code and focused tests are grouped in `saleswiki_mcp/`,
`integrations/workbench/`, and `tests/`. See [Vercel setup](docs/VERCEL.en.md)
to deploy the static interface preview.

## Demo boundary

All included records and users are synthetic. The hosted Workbench is a static
preview; it does not connect to a CRM or authenticate real users. The local
service is an implementation demo, not a production deployment or a claim that
the design has been validated in a live customer environment. Do not add real
customer records, credentials, private notes, or unpublished articles.

Licensed under MIT. Keep the copyright and license notice with copies and
substantial portions of this software.
