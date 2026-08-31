#!/usr/bin/env python3
"""Build Markdown dashboard snapshots from SalesWiki derived indexes."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def scalar(row: dict[str, object], key: str) -> str:
    return str(row.get(key) or "")


def link(row: dict[str, object], link_prefix: str = "") -> str:
    name = scalar(row, "canonical_name") or scalar(row, "path")
    path = scalar(row, "path")
    if not path:
        return name
    # Card paths are stored relative to the vault root. Snapshots live in a
    # separate output directory, so prefix the path with the relative hop from
    # the output dir back to the vault (e.g. ../../demo-vault) or the link would
    # resolve next to the snapshot instead of at the real card.
    target = f"{link_prefix}/{path}" if link_prefix else path
    return f"[{name}]({target})"


def markdown_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["No rows."]
    lines = ["| " + " | ".join(markdown_cell(header) for header in headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(cell) for cell in row) + " |")
    return lines


def top_rows(rows: list[dict[str, object]], limit: int = 10) -> list[dict[str, object]]:
    return rows[:limit]


def build_sales_today(entities: list[dict[str, object]], freshness: list[dict[str, object]], link_prefix: str = "") -> str:
    freshness_by_id = {scalar(row, "entity_id"): row for row in freshness}
    action_rows = []
    for row in entities:
        if scalar(row, "type") not in {"lead", "task", "deal"}:
            continue
        fresh = freshness_by_id.get(scalar(row, "entity_id"), {})
        if scalar(fresh, "freshness") == "needs-action" or scalar(row, "type") in {"task", "lead"}:
            action_rows.append(
                [
                    link(row, link_prefix),
                    scalar(row, "type"),
                    scalar(row, "owner"),
                    scalar(row, "company"),
                    scalar(row, "score"),
                    scalar(row, "score_band"),
                    scalar(fresh, "freshness"),
                    scalar(fresh, "next_review"),
                ]
            )
    lines = ["# Sales Today", "", "Action-oriented sales snapshot.", ""]
    lines += table(["Item", "Type", "Owner", "Company", "Score", "Band", "Freshness", "Next Review"], top_rows(action_rows))
    return "\n".join(lines) + "\n"


def build_deal_risk(entities: list[dict[str, object]], freshness: list[dict[str, object]], link_prefix: str = "") -> str:
    freshness_by_id = {scalar(row, "entity_id"): row for row in freshness}
    deal_rows = []
    for row in entities:
        if scalar(row, "type") != "deal":
            continue
        fresh = freshness_by_id.get(scalar(row, "entity_id"), {})
        deal_rows.append([link(row, link_prefix), scalar(row, "owner"), scalar(fresh, "freshness"), scalar(row, "access")])
    lines = ["# Deal Risk", "", "Deals that need review, action or sync.", ""]
    lines += table(["Deal", "Owner", "Freshness", "Access"], top_rows(deal_rows))
    return "\n".join(lines) + "\n"


def build_monitoring(entities: list[dict[str, object]], freshness: list[dict[str, object]], link_prefix: str = "") -> str:
    entity_by_id = {scalar(row, "entity_id"): row for row in entities}
    monitoring_rows = []
    for fresh in freshness:
        entity = entity_by_id.get(scalar(fresh, "entity_id"), {})
        if scalar(fresh, "next_check") or scalar(fresh, "freshness") in {"stale", "needs-research"}:
            monitoring_rows.append([link(entity, link_prefix), scalar(fresh, "type"), scalar(fresh, "owner"), scalar(fresh, "freshness"), scalar(fresh, "next_check")])
    lines = ["# Monitoring", "", "Entities due for review or monitoring.", ""]
    lines += table(["Entity", "Type", "Owner", "Freshness", "Next Check"], top_rows(monitoring_rows))
    return "\n".join(lines) + "\n"


def build_marketing_insights(entities: list[dict[str, object]], link_prefix: str = "") -> str:
    marketing_types = {"topic", "pain-point", "objection", "use-case", "campaign", "content-brief", "asset", "experiment"}
    insight_rows = []
    for row in entities:
        if scalar(row, "type") in marketing_types:
            insight_rows.append([link(row, link_prefix), scalar(row, "type"), scalar(row, "owner"), scalar(row, "status"), scalar(row, "confidence"), scalar(row, "access")])
    lines = ["# Marketing Insights", "", "Topics, pains, objections, campaigns and assets for marketing follow-up.", ""]
    lines += table(["Insight", "Type", "Owner", "Status", "Confidence", "Access"], top_rows(insight_rows))
    return "\n".join(lines) + "\n"


def build_data_quality(entities: list[dict[str, object]], freshness: list[dict[str, object]]) -> str:
    counts = Counter(scalar(row, "type") for row in entities)
    freshness_counts = Counter(scalar(row, "freshness") for row in freshness if scalar(row, "freshness"))
    lines = ["# Data Quality", "", f"Generated: {date.today().isoformat()}", ""]
    lines.append("## Entity Counts")
    lines += table(["Type", "Count"], [[key, str(value)] for key, value in sorted(counts.items())])
    lines.append("")
    lines.append("## Freshness Counts")
    lines += table(["Freshness", "Count"], [[key, str(value)] for key, value in sorted(freshness_counts.items())])
    return "\n".join(lines) + "\n"


def build_snapshot_index(output_root: Path) -> str:
    files = [
        ("Sales Today", "sales-today.md"),
        ("Deal Risk", "deal-risk.md"),
        ("Monitoring", "monitoring.md"),
        ("Marketing Insights", "marketing-insights.md"),
        ("Data Quality", "data-quality.md"),
    ]
    lines = ["# Dashboard Snapshots", "", "Generated Markdown snapshots for users who do not need Obsidian Bases.", ""]
    for label, filename in files:
        lines.append(f"- [{label}]({filename})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SalesWiki Markdown dashboard snapshots.")
    parser.add_argument("--index-root", default=str(PROJECT_ROOT / "indexes"), help="Index root produced by build_indexes.py.")
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "reports" / "dashboard-snapshots"), help="Output directory for Markdown snapshots.")
    parser.add_argument("--vault-root", default=str(PROJECT_ROOT), help="Vault root the card paths are relative to; used to rebase links from the output dir.")
    args = parser.parse_args()

    index_root = Path(args.index_root).resolve()
    output_root = Path(args.output_root).resolve()
    vault_root = Path(args.vault_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    # Relative hop from the snapshot output dir back to the vault root, so a
    # vault-relative card path resolves from the snapshot's own location.
    link_prefix = os.path.relpath(vault_root, output_root).replace(os.sep, "/")

    entities = read_jsonl(index_root / "entities" / "entities.jsonl")
    freshness = read_jsonl(index_root / "freshness" / "freshness.jsonl")

    snapshots = {
        "index.md": build_snapshot_index(output_root),
        "sales-today.md": build_sales_today(entities, freshness, link_prefix),
        "deal-risk.md": build_deal_risk(entities, freshness, link_prefix),
        "monitoring.md": build_monitoring(entities, freshness, link_prefix),
        "marketing-insights.md": build_marketing_insights(entities, link_prefix),
        "data-quality.md": build_data_quality(entities, freshness),
    }

    for filename, content in snapshots.items():
        (output_root / filename).write_text(content, encoding="utf-8")

    print("SalesWiki dashboard snapshots")
    print(f"entities: {len(entities)}")
    print(f"freshness: {len(freshness)}")
    print(f"output: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
