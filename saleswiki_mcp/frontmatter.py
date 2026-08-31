"""Minimal YAML-frontmatter reader for SalesWiki Markdown cards.

Handles the atomic key: value and simple list properties SalesWiki uses; it does
not aim to be a full YAML parser. Returns (properties, body).
"""

from __future__ import annotations


def parse(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    props: dict[str, str] = {}
    current_list_key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            current_list_key = None
            continue
        if raw.startswith("  - ") and current_list_key:
            props.setdefault(current_list_key + "[]", "")
            props[current_list_key + "[]"] += raw.strip()[2:].strip() + "\n"
            continue
        if ":" in raw and not raw.startswith(" "):
            key, _, value = raw.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                current_list_key = key
            else:
                props[key] = value
                current_list_key = None
    body = "\n".join(lines[end + 1:]).strip("\n")
    return props, body
