# Indexes

This folder stores derived search and graph artifacts.

Do not treat files here as the source of truth. Rebuild them from `raw/` and `wiki/`.

Generated indexes:

- `entities/entity-registry.csv` - stable entity registry for IDs, names, paths, external IDs and access labels.
- `entities/entities.jsonl` - normalized entity records from card frontmatter.
- `fulltext/documents.jsonl` - document inventory for search/indexing.
- `freshness/freshness.jsonl` - review, monitoring and freshness records.
- `graph/edges.jsonl` - wikilink-derived graph edges.
- `temporal/events.jsonl` - date-bearing entity events.
- `vectors/` - optional semantic search index over compiled wiki pages.

Rebuild:

```bash
python3 scripts/build_indexes.py
```

The script skips `_template.md` files and updates `state/index-status.md`.
