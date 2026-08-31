#!/usr/bin/env python3
"""Build derived SalesWiki indexes from Markdown entity cards.

The Markdown vault remains the source of truth. This script emits machine-readable
derived files that can be rebuilt at any time.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTITY_CARD_GLOB = "wiki/entities/*/*.md"


class IndexBuildError(Exception):
    """Raised when derived indexes cannot be built safely."""


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_scalar(value: str) -> str:
    return value.strip().strip("\"'")


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text

    data: dict[str, object] = {}
    current_key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            value = data.setdefault(current_key, [])
            if isinstance(value, list):
                value.append(clean_scalar(line[4:].strip()))
            continue
        if ":" not in line or line.startswith(" "):
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        current_key = key
        if value == "[]":
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [clean_scalar(item.strip()) for item in value[1:-1].split(",") if item.strip()]
        else:
            data[key] = clean_scalar(value)
    return data, text[end + 5 :]


def scalar(value: object) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value or "")


def values(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value:
        return [str(value)]
    return []


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "unnamed"


def normalized_name(path: Path) -> str:
    return re.sub(r"\s+", " ", path.stem).strip().casefold()


def wikilinks(body: str) -> list[str]:
    targets: list[str] = []
    for match in re.finditer(r"\[\[([^\]]+)\]\]", body):
        target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
        if target and not any(ch in target for ch in "<>"):
            targets.append(target)
    return targets


def iter_cards(source_root: Path) -> list[tuple[Path, dict[str, object], str]]:
    cards: list[tuple[Path, dict[str, object], str]] = []
    for path in sorted(source_root.glob(ENTITY_CARD_GLOB)):
        if path.name == "_template.md":
            continue
        text = read(path)
        fm, body = split_frontmatter(text)
        if fm.get("type"):
            cards.append((path, fm, body))
    return cards


def entity_id_for(path: Path, fm: dict[str, object], allow_generated_ids: bool) -> str:
    explicit = scalar(fm.get("entity_id")).strip()
    if explicit:
        return explicit
    if not allow_generated_ids:
        raise IndexBuildError(f"{path}: missing required `entity_id`; run health_check.py or pass --allow-generated-ids for fixtures")
    card_type = scalar(fm.get("type")) or "entity"
    return f"{card_type}-{slug(path.stem)}"


def relation_for_field(card_type: str, field: str) -> str:
    mapping = {
        ("person", "company"): "PERSON_WORKS_AT_COMPANY",
        ("lead", "company"): "LEAD_BELONGS_TO_COMPANY",
        ("lead", "deal"): "LEAD_RELATED_TO_DEAL",
        ("deal", "company"): "DEAL_WITH_COMPANY",
        ("call", "company"): "CALL_RELATED_TO_COMPANY",
        ("call", "deal"): "CALL_RELATED_TO_DEAL",
        ("call", "participants"): "CALL_HAS_PARTICIPANT",
        ("event-participation", "event"): "EVENT_PARTICIPATION_FOR_EVENT",
        ("event-participation", "company"): "COMPANY_PARTICIPATES_IN_EVENT",
        ("event-participation", "person"): "PERSON_PARTICIPATES_IN_EVENT",
        ("*", "source_id"): "ENTITY_SUPPORTED_BY_SOURCE",
        ("*", "duplicate_of"): "DUPLICATE_OF",
        ("*", "corroborates"): "CORROBORATES",
    }
    return mapping.get((card_type, field), mapping.get(("*", field), f"FIELD_{field.upper()}"))


def target_from_wikilink(value: str) -> str | None:
    match = re.search(r"\[\[([^\]]+)\]\]", value)
    if not match:
        return None
    target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
    if not target or any(ch in target for ch in "<>"):
        return None
    return target


def semantic_edges(
    entity_id: str,
    rel_path: str,
    card_type: str,
    fm: dict[str, object],
    entity_by_stem: dict[str, str],
) -> list[dict[str, object]]:
    graph: list[dict[str, object]] = []
    fields = ("company", "deal", "participants", "event", "person", "source_id", "duplicate_of", "corroborates")
    for field in fields:
        for raw_value in values(fm.get(field)):
            if not raw_value:
                continue
            relation = relation_for_field(card_type, field)
            target = target_from_wikilink(raw_value)
            edge = {
                "from_entity_id": entity_id,
                "from_path": rel_path,
                "relation": relation,
                "source_field": field,
            }
            if target:
                edge["to_page"] = target
                edge["to_entity_id"] = entity_by_stem.get(target, "")
            elif field == "source_id":
                edge["to_source_id"] = raw_value
            elif field in {"duplicate_of", "corroborates"}:
                edge["to_reference"] = raw_value
            else:
                edge["to_value"] = raw_value
            graph.append(edge)
    return graph


def edge_key(edge: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(value)) for key, value in edge.items()))


def append_unique_edge(graph: list[dict[str, object]], seen_edges: set[tuple[tuple[str, str], ...]], edge: dict[str, object]) -> None:
    key = edge_key(edge)
    if key in seen_edges:
        return
    seen_edges.add(key)
    graph.append(edge)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_registry(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "entity_id",
        "type",
        "canonical_name",
        "normalized_name",
        "path",
        "aliases",
        "external_ids",
        "deletion_status",
        "access",
        "updated",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def update_index_status(state_path: Path, row_counts: dict[str, int]) -> None:
    today = date.today().isoformat()
    rows = [
        ("fulltext", "wiki", row_counts["fulltext"], "built-empty" if row_counts["fulltext"] == 0 else "built"),
        ("entities", "wiki/entities", row_counts["entities"], "built-empty" if row_counts["entities"] == 0 else "built"),
        ("freshness", "wiki/state/tracking", row_counts["freshness"], "built-empty" if row_counts["freshness"] == 0 else "built"),
        ("temporal", "news/events/calls/deals", row_counts["temporal"], "built-empty" if row_counts["temporal"] == 0 else "built"),
        ("graph-export", "wikilinks/properties", row_counts["graph"], "built-empty" if row_counts["graph"] == 0 else "built"),
        ("vectors", "wiki", 0, "optional"),
    ]
    lines = [
        "# Index Status",
        "",
        "Track the state of derived indexes and graph exports.",
        "",
        "| index | scope | last_rebuild | status | stale_reason | next_rebuild_due | notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, scope, count, status in rows:
        note = "Obsidian graph itself updates inside Obsidian." if name == "graph-export" else f"{count} rows"
        lines.append(f"| {name} | {scope} | {today} | {status} |  |  | {note} |")
    lines.append("")
    state_path.write_text("\n".join(lines), encoding="utf-8")


def build(source_root: Path, output_root: Path, update_state: bool, allow_generated_ids: bool) -> dict[str, int]:
    cards = iter_cards(source_root)
    entity_by_stem: dict[str, str] = {}
    entities: list[dict[str, object]] = []
    freshness: list[dict[str, object]] = []
    temporal: list[dict[str, object]] = []
    fulltext: list[dict[str, object]] = []

    for path, fm, body in cards:
        rel = path.relative_to(source_root).as_posix()
        entity_id = entity_id_for(path, fm, allow_generated_ids)
        card_type = scalar(fm.get("type"))
        entity_by_stem[path.stem] = entity_id
        aliases = fm.get("aliases", [])
        external_ids = [scalar(fm.get("hubspot_id")), scalar(fm.get("source_id"))]
        entities.append(
            {
                "entity_id": entity_id,
                "type": card_type,
                "canonical_name": path.stem,
                "normalized_name": normalized_name(path),
                "path": rel,
                "aliases": scalar(aliases),
                "external_ids": "|".join(value for value in external_ids if value),
                "deletion_status": scalar(fm.get("deletion_status")),
                "access": scalar(fm.get("access")),
                "updated": scalar(fm.get("updated")),
                "owner": scalar(fm.get("owner")),
                "company": scalar(fm.get("company")),
                "status": scalar(fm.get("status")),
                "confidence": scalar(fm.get("confidence") or fm.get("score_confidence")),
                "score": scalar(fm.get("score")),
                "score_band": scalar(fm.get("score_band")),
                "source_id": scalar(fm.get("source_id")),
                "raw_path": scalar(fm.get("raw_path")),
            }
        )

        if fm.get("freshness") or fm.get("next_review") or fm.get("next_check"):
            freshness.append(
                {
                    "entity_id": entity_id,
                    "type": card_type,
                    "path": rel,
                    "freshness": scalar(fm.get("freshness")),
                    "last_reviewed": scalar(fm.get("last_reviewed")),
                    "last_checked": scalar(fm.get("last_checked")),
                    "next_review": scalar(fm.get("next_review")),
                    "next_check": scalar(fm.get("next_check")),
                    "owner": scalar(fm.get("owner") or fm.get("monitoring_owner")),
                }
            )

        for field in ("created", "updated", "date", "date_published", "date_collected", "close_date", "scored_at"):
            value = scalar(fm.get(field))
            if value:
                temporal.append({"entity_id": entity_id, "type": card_type, "path": rel, "date_field": field, "date": value})

        fulltext.append(
            {
                "entity_id": entity_id,
                "type": card_type,
                "path": rel,
                "title": path.stem,
                "text_chars": len(body),
                "wikilink_count": len(wikilinks(body)),
            }
        )

    graph: list[dict[str, object]] = []
    seen_edges: set[tuple[tuple[str, str], ...]] = set()
    for path, fm, body in cards:
        rel = path.relative_to(source_root).as_posix()
        entity_id = entity_id_for(path, fm, allow_generated_ids)
        card_type = scalar(fm.get("type"))
        for target in wikilinks(body):
            append_unique_edge(
                graph,
                seen_edges,
                {
                    "from_entity_id": entity_id,
                    "from_path": rel,
                    "relation": "WIKILINKS_TO",
                    "to_page": target,
                    "to_entity_id": entity_by_stem.get(target, ""),
                },
            )
        for edge in semantic_edges(entity_id, rel, card_type, fm, entity_by_stem):
            append_unique_edge(graph, seen_edges, edge)

    write_registry(output_root / "entities" / "entity-registry.csv", entities)
    write_jsonl(output_root / "entities" / "entities.jsonl", entities)
    write_jsonl(output_root / "freshness" / "freshness.jsonl", freshness)
    write_jsonl(output_root / "temporal" / "events.jsonl", temporal)
    write_jsonl(output_root / "graph" / "edges.jsonl", graph)
    write_jsonl(output_root / "fulltext" / "documents.jsonl", fulltext)

    row_counts = {
        "entities": len(entities),
        "freshness": len(freshness),
        "temporal": len(temporal),
        "graph": len(graph),
        "fulltext": len(fulltext),
    }
    if update_state:
        update_index_status(source_root / "state" / "index-status.md", row_counts)
    return row_counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SalesWiki derived indexes.")
    parser.add_argument("--source-root", default=str(PROJECT_ROOT), help="Vault root to read. Defaults to project root.")
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "indexes"), help="Directory for generated indexes.")
    parser.add_argument("--no-update-state", action="store_true", help="Do not update state/index-status.md.")
    parser.add_argument("--allow-generated-ids", action="store_true", help="Allow filename-derived IDs. Intended for synthetic fixtures only.")
    parser.add_argument("--expect-counts", help="Optional JSON file with expected row counts for validation.")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve()
    try:
        row_counts = build(
            source_root,
            output_root,
            update_state=not args.no_update_state,
            allow_generated_ids=args.allow_generated_ids,
        )
    except IndexBuildError as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.expect_counts:
        expected = json.loads(Path(args.expect_counts).read_text(encoding="utf-8"))
        mismatches = []
        for key, expected_value in sorted(expected.items()):
            actual_value = row_counts.get(key)
            if actual_value != expected_value:
                mismatches.append(f"{key}: expected {expected_value}, got {actual_value}")
        if mismatches:
            print("ERROR: index count expectations failed")
            for mismatch in mismatches:
                print(mismatch)
            return 1

    print("SalesWiki index build")
    for name in ("entities", "freshness", "temporal", "graph", "fulltext"):
        print(f"{name}: {row_counts[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
