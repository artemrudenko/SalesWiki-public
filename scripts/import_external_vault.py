#!/usr/bin/env python3
"""Plan and stage an approved external Markdown/Obsidian vault import.

This script intentionally does not create SalesWiki entity cards from arbitrary
external notes. It produces a reviewed import package that an agent/curator can
map into typed cards after the user approves scope and access decisions.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import audit_external_vault


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TYPES = {"company", "person", "deal", "call", "source", "marketing-knowledge"}


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("external-vault-%Y%m%dT%H%M%SZ")


def split_csv(value: str | None) -> set[str]:
    if not value:
        return set(DEFAULT_TYPES)
    return {item.strip() for item in value.split(",") if item.strip()}


def has_sensitive_signal(path: Path, rel: str) -> bool:
    if path.suffix.lower() not in audit_external_vault.TEXT_EXTENSIONS:
        return False
    text = audit_external_vault.read_text(path)
    return any(pattern.search(text) or pattern.search(rel) for pattern in audit_external_vault.SENSITIVE_PATTERNS.values())


def excluded(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in patterns)


def discover(source: Path, include_types: set[str], exclude_patterns: list[str], allow_sensitive: bool, include_attachments: bool) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(source).as_posix()
        if excluded(rel, exclude_patterns):
            continue

        suffix = path.suffix.lower()
        is_text = suffix in audit_external_vault.TEXT_EXTENSIONS
        is_attachment = suffix in audit_external_vault.ATTACHMENT_EXTENSIONS
        if not is_text and not (include_attachments and is_attachment):
            continue

        text = audit_external_vault.read_text(path) if is_text else ""
        inferred_type = audit_external_vault.likely_type(path, text) if is_text else "attachment"
        sensitive = has_sensitive_signal(path, rel) if is_text else False
        action = "stage"
        reason = ""
        if is_text and inferred_type not in include_types:
            action = "skip"
            reason = f"type `{inferred_type}` not in selected scope"
        if sensitive and not allow_sensitive:
            action = "skip"
            reason = "sensitive signal; rerun with explicit --allow-sensitive after permission boundary approval"
        rows.append(
            {
                "path": rel,
                "kind": "text" if is_text else "attachment",
                "likely_type": inferred_type,
                "sensitive": sensitive,
                "action": action,
                "reason": reason,
            }
        )
    return rows


def markdown_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def render_plan(run_id: str, source: Path, rows: list[dict[str, object]], report: dict[str, object], copy_files: bool) -> str:
    staged = [row for row in rows if row["action"] == "stage"]
    skipped = [row for row in rows if row["action"] == "skip"]
    lines = [
        "# External Vault Import Plan",
        "",
        f"Run ID: `{run_id}`",
        f"Source: `{source}`",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Summary",
        "",
        f"- Markdown/text files found: {report['markdown_count']}",
        f"- Attachments found: {report['attachment_count']}",
        f"- Files selected for staging: {len(staged)}",
        f"- Files skipped: {len(skipped)}",
        f"- Copy files on execute: {'yes' if copy_files else 'no, reference-only manifest'}",
        "",
        "## Staged Files",
        "",
    ]
    if staged:
        lines += ["| Path | Likely Type | Sensitive |", "| --- | --- | --- |"]
        for row in staged:
            lines.append(f"| {markdown_cell(row['path'])} | {markdown_cell(row['likely_type'])} | {markdown_cell(row['sensitive'])} |")
    else:
        lines.append("No rows.")

    lines += ["", "## Skipped Files", ""]
    if skipped:
        lines += ["| Path | Likely Type | Reason |", "| --- | --- | --- |"]
        for row in skipped:
            lines.append(f"| {markdown_cell(row['path'])} | {markdown_cell(row['likely_type'])} | {markdown_cell(row['reason'])} |")
    else:
        lines.append("No rows.")

    lines += [
        "",
        "## Next Mapping Questions",
        "",
        "- Which staged files should create/update Company, Person, Lead, Deal, Call or marketing knowledge cards?",
        "- Which external fields/tags map to SalesWiki properties?",
        "- Which files should stay as raw evidence only?",
        "- Which sensitive files require `personal-data`, `sales-confidential` or `legal-review` access?",
        "",
        "## Execution Notes",
        "",
        "- This plan stages external files/references only; it does not overwrite production entity cards.",
        "- A curator or import assistant should turn staged files into typed SalesWiki cards after mapping approval.",
        "",
    ]
    return "\n".join(lines)


def append_ingest_run(project_root: Path, run_id: str, source: Path, staged_count: int, copy_files: bool) -> None:
    path = project_root / "state" / "ingest-runs.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Ingest Runs\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n## {run_id}\n\n"
            f"- Type: external-vault-import\n"
            f"- Source: `{source}`\n"
            f"- Staged files: {staged_count}\n"
            f"- Copy files: {'yes' if copy_files else 'no, reference-only'}\n"
            f"- Status: staged\n"
        )


def execute(project_root: Path, source: Path, run_id: str, rows: list[dict[str, object]], plan_markdown: str, plan_json: dict[str, object], copy_files: bool) -> None:
    plan_root = project_root / "state" / "import-plans"
    raw_root = project_root / "raw" / "imports" / run_id
    plan_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)

    (plan_root / f"{run_id}.md").write_text(plan_markdown, encoding="utf-8")
    (plan_root / f"{run_id}.json").write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (raw_root / "manifest.json").write_text(json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")

    if copy_files:
        files_root = raw_root / "files"
        for row in rows:
            if row["action"] != "stage":
                continue
            src = source / str(row["path"])
            dst = files_root / str(row["path"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    append_ingest_run(project_root, run_id, source, sum(1 for row in rows if row["action"] == "stage"), copy_files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan and stage an external Markdown/Obsidian vault import.")
    parser.add_argument("--source", required=True, help="External vault/folder path.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="SalesWiki project root.")
    parser.add_argument("--run-id", default=now_id(), help="Stable import run ID.")
    parser.add_argument("--include-types", help="Comma-separated likely types to stage. Default: company,person,deal,call,source,marketing-knowledge.")
    parser.add_argument("--exclude", action="append", default=[], help="Glob pattern to exclude, relative to source. Can be repeated.")
    parser.add_argument("--include-attachments", action="store_true", help="Include attachments in staging manifest.")
    parser.add_argument("--allow-sensitive", action="store_true", help="Allow files with sensitive signals after explicit permission boundary approval.")
    parser.add_argument("--copy-files", action="store_true", help="Copy staged files into raw/imports/<run-id>/files/. Default is reference-only.")
    parser.add_argument("--execute", action="store_true", help="Write plan and raw/import staging package. Without this, prints dry-run only.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    project_root = Path(args.project_root).resolve()
    if not source.is_dir():
        print(f"ERROR: source is not a directory: {source}")
        return 1
    if not project_root.is_dir():
        print(f"ERROR: project root is not a directory: {project_root}")
        return 1

    report = audit_external_vault.audit(source)
    rows = discover(source, split_csv(args.include_types), args.exclude, args.allow_sensitive, args.include_attachments)
    plan_json = {
        "run_id": args.run_id,
        "source": str(source),
        "execute": args.execute,
        "copy_files": args.copy_files,
        "audit": report,
        "files": rows,
    }
    plan_markdown = render_plan(args.run_id, source, rows, report, args.copy_files)

    if args.execute:
        execute(project_root, source, args.run_id, rows, plan_markdown, plan_json, args.copy_files)
        print(f"Staged import package: {project_root / 'raw' / 'imports' / args.run_id}")
        print(f"Import plan: {project_root / 'state' / 'import-plans' / (args.run_id + '.md')}")
    else:
        print(plan_markdown)
        print("Dry run only. Re-run with --execute after user approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
