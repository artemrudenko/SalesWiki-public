# Index Status

Track the state of derived indexes and graph exports.

| index | scope | last_rebuild | status | stale_reason | next_rebuild_due | notes |
| --- | --- | --- | --- | --- | --- | --- |
| fulltext | wiki | 2026-08-20 | built-empty |  |  | 0 production rows; public snapshot contains templates/process docs and synthetic demo data only. |
| entities | wiki/entities | 2026-08-20 | built-empty |  |  | 0 production entity rows. |
| freshness | wiki/state/tracking | 2026-08-20 | built-empty |  |  | 0 production rows after public cleanup. |
| temporal | news/events/calls/deals | 2026-08-20 | built-empty |  |  | 0 production temporal rows. |
| graph-export | wikilinks/properties | 2026-08-20 | built-empty |  |  | Obsidian graph itself updates inside Obsidian. |
| vectors | wiki | 2026-08-20 | optional |  |  | 0 rows; vector search remains out of scope for the public starter kit. |
