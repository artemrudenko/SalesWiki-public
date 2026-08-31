#!/usr/bin/env python3
"""Read-only audit of an external Markdown/Obsidian vault for SalesWiki import planning."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
ATTACHMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".mp3", ".mp4", ".mov", ".m4a"}
SENSITIVE_PATTERNS = {
    "transcript": re.compile(r"\b(transcript|recording|call|meeting)\b", re.IGNORECASE),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\+?\d[\d\s().-]{7,}\d"),
    "crm": re.compile(r"\b(crm|hubspot|deal|pipeline|pricing|contract)\b", re.IGNORECASE),
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def frontmatter_keys(text: str) -> list[str]:
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---", 4)
    if end == -1:
        return []
    keys = []
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            keys.append(line.split(":", 1)[0].strip())
    return keys


def wikilinks(text: str) -> list[str]:
    return [match.group(1).split("|", 1)[0].split("#", 1)[0].strip() for match in re.finditer(r"\[\[([^\]]+)\]\]", text)]


def likely_type(path: Path, text: str) -> str:
    haystack = f"{path.as_posix()}\n{text[:2000]}".lower()
    checks = [
        ("call", ("transcript", "meeting", "call notes", "recording")),
        ("deal", ("deal", "opportunity", "proposal", "close date", "pricing")),
        ("person", ("person", "contact", "linkedin", "email")),
        ("company", ("company", "account", "customer", "prospect")),
        ("source", ("source", "url", "article", "news")),
        ("marketing-knowledge", ("campaign", "content", "persona", "pain", "objection")),
    ]
    for card_type, terms in checks:
        if any(term in haystack for term in terms):
            return card_type
    return "unknown"


def audit(source: Path) -> dict[str, object]:
    markdown_files = []
    attachment_files = []
    other_files = []
    folders = set()
    frontmatter_counter: Counter[str] = Counter()
    wikilink_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    sensitive_counter: Counter[str] = Counter()
    sample_candidates = []

    for path in sorted(source.rglob("*")):
        if path.is_dir():
            folders.add(path.relative_to(source).as_posix())
            continue
        suffix = path.suffix.lower()
        rel = path.relative_to(source).as_posix()
        if suffix in TEXT_EXTENSIONS:
            markdown_files.append(rel)
            text = read_text(path)
            frontmatter_counter.update(frontmatter_keys(text))
            wikilink_counter.update(wikilinks(text))
            inferred = likely_type(path, text)
            type_counter[inferred] += 1
            if len(sample_candidates) < 30:
                sample_candidates.append({"path": rel, "likely_type": inferred})
            for name, pattern in SENSITIVE_PATTERNS.items():
                if pattern.search(text) or pattern.search(rel):
                    sensitive_counter[name] += 1
        elif suffix in ATTACHMENT_EXTENSIONS:
            attachment_files.append(rel)
        else:
            other_files.append(rel)

    return {
        "source": str(source),
        "folder_count": len(folders),
        "markdown_count": len(markdown_files),
        "attachment_count": len(attachment_files),
        "other_file_count": len(other_files),
        "top_frontmatter_keys": frontmatter_counter.most_common(30),
        "top_wikilinks": wikilink_counter.most_common(30),
        "likely_type_counts": type_counter.most_common(),
        "sensitive_signal_counts": sensitive_counter.most_common(),
        "sample_candidates": sample_candidates,
    }


def render_markdown(report: dict[str, object]) -> str:
    def cell(value: object) -> str:
        return str(value).replace("\n", " ").replace("|", "\\|")

    lines = ["# External Vault Audit", "", f"Source: `{report['source']}`", ""]
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Folders: {report['folder_count']}")
    lines.append(f"- Markdown/text files: {report['markdown_count']}")
    lines.append(f"- Attachments: {report['attachment_count']}")
    lines.append(f"- Other files: {report['other_file_count']}")
    lines.append("")

    for title, key in (
        ("Likely Types", "likely_type_counts"),
        ("Sensitive Signals", "sensitive_signal_counts"),
        ("Top Frontmatter Keys", "top_frontmatter_keys"),
        ("Top Wikilinks", "top_wikilinks"),
    ):
        lines.append(f"## {title}")
        rows = report[key]
        if not rows:
            lines.append("")
            lines.append("No rows.")
        else:
            lines.append("")
            lines.append("| Value | Count |")
            lines.append("| --- | --- |")
            for value, count in rows:
                lines.append(f"| {cell(value)} | {cell(count)} |")
        lines.append("")

    lines.append("## Sample Candidates")
    lines.append("")
    lines.append("| Path | Likely Type |")
    lines.append("| --- | --- |")
    for row in report["sample_candidates"]:
        lines.append(f"| {cell(row['path'])} | {cell(row['likely_type'])} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an external Markdown/Obsidian vault before SalesWiki import.")
    parser.add_argument("--source", required=True, help="External vault/folder path to audit.")
    parser.add_argument("--output", help="Optional Markdown report path.")
    parser.add_argument("--json-output", help="Optional JSON report path.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        print(f"ERROR: source is not a directory: {source}")
        return 1

    report = audit(source)
    markdown = render_markdown(report)
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
    if args.json_output:
        output = Path(args.json_output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
