"""Section extraction and brief rendering helpers."""

from __future__ import annotations


def extract_section(body: str, heading: str) -> str:
    """Return the text under a `## heading` until the next `## ` heading."""
    target = f"## {heading}".lower()
    out: list[str] = []
    capture = False
    for line in body.splitlines():
        if line.strip().lower().startswith("## "):
            if capture:
                break
            capture = line.strip().lower() == target
            continue
        if capture:
            out.append(line)
    return "\n".join(out).strip()


def find_bullet(section: str, label: str) -> str:
    """Return the text after `- {label}:` within a section, or '' if absent."""
    needle = f"- {label}".lower()
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(needle):
            _, _, rest = stripped.partition(":")
            return rest.strip()
    return ""


def field_value(body: str, spec: dict) -> str:
    """Extract a logical field from a card body using a field-extraction spec
    ({"section": ...} for a whole section, plus optional {"label": ...} for a
    labeled bullet). Decouples extraction from any one card shape.
    """
    section = extract_section(body, spec.get("section", ""))
    label = spec.get("label")
    return find_bullet(section, label) if label else section


def wikilink_targets(section: str, prefix: str = "") -> list[str]:
    """Return `[[...]]` link targets in a section, optionally stripping a prefix.

    `wikilink_targets(text, "Company - ")` turns `- [[Company - Atlas Foods]]`
    into `["Atlas Foods"]`.
    """
    targets: list[str] = []
    rest = section
    while "[[" in rest:
        start = rest.index("[[") + 2
        end = rest.find("]]", start)
        if end == -1:
            break
        target = rest[start:end].strip()
        if prefix and target.startswith(prefix):
            target = target[len(prefix):]
        targets.append(target)
        rest = rest[end + 2:]
    return targets


def add_bullet_to_section(text: str, heading: str, bullet: str) -> str:
    """Append `- {bullet}` to the end of a `## heading` section, creating the
    section at the end of the document if it does not exist.
    """
    lines = text.splitlines()
    target = f"## {heading}".lower()
    start = next((index for index, line in enumerate(lines) if line.strip().lower() == target), None)
    if start is None:
        return text.rstrip("\n") + f"\n\n## {heading}\n\n- {bullet}\n"
    end = next((j for j in range(start + 1, len(lines)) if lines[j].strip().lower().startswith("## ")), len(lines))
    insert_at = end
    while insert_at - 1 > start and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    lines.insert(insert_at, f"- {bullet}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def remove_lines_containing(text: str, needle: str) -> str:
    """Return text with every line containing `needle` removed."""
    kept = [line for line in text.splitlines() if needle not in line]
    return "\n".join(kept) + ("\n" if text.endswith("\n") else "")


def find_handle(body: str) -> str:
    idx = body.find("restricted://")
    if idx == -1:
        return "restricted://(unknown)"
    return body[idx:].split()[0].strip()
