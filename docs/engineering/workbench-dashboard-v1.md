# Workbench Dashboard v1

The Workbench home is the **Today** dashboard. It supports a decision moment,
not generic reporting: what changed, what is covered, and what new evidence
needs attention.

## Current synthetic-demo widgets

| Widget | Decision it supports | Input | Access behaviour |
| --- | --- | --- | --- |
| Risk momentum | Which visible account needs intervention first? | Explicit synthetic seven-day score history | Hidden for the marketing fixture role; it is commercial context. |
| Account coverage | Is a decision ready to progress? | Visible graph: economic buyer, next step, verified evidence, monitoring plan | Rows are built only from companies visible to the selected fixture role. |
| Signal timeline | What new dated evidence should I inspect? | Visible account source cards | Emits only source title, account and date already present in the graph fixture. |

The score history is explicitly marked **Synthetic demo data**. It is not a
forecast, production metric or LLM-generated score. This prevents the demo
from pretending that a trend exists where a real vault has only one snapshot.

## Implemented server read model

The browser must not aggregate a complete company list or source corpus itself.
`saleswiki.dashboard` now produces the versioned `saleswiki.dashboard-view` v1
read model after policy filtering, in the same manner as `company_search` and
`entity_graph`. The Workbench BFF exposes it at `GET /api/v1/dashboard`; the
response is private (`Cache-Control: no-store`) and the browser accepts only
the narrow contract.

The synthetic permissioned demo supplies dated observations under
`state/dashboard-observations.jsonl`. A trend is shown only after two visible
observations; otherwise the response reports `insufficient-history`. A real
pilot must use an approved observation writer in its separate pilot vault — it
must not copy customer history into this repository.

LLM use remains optional and outside this read model: it may explain a
role-filtered dashboard response, but it never determines access, calculates
the source-of-truth metric or invents historical points.
