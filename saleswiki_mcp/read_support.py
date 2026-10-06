"""Pure helpers shared by composed read products.

This module intentionally has no policy, retrieval, audit or transport imports.
It keeps presentation and roll-up helpers outside the application facade.
"""

from __future__ import annotations


def as_bullets(section_text: str) -> list[str]:
    return [line.strip().lstrip("-").strip() for line in section_text.splitlines() if line.strip()]


def strip_title(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip() + "\n"


_EMBED_DROP_PREFIXES = ("**Conclusion:**", "**Confidence:**", "**Freshness:**", "**Sources:**", "**Next action:**", "**Access:**", "📎")


def embed_body(text: str) -> str:
    return "\n".join(line for line in strip_title(text).splitlines() if not line.strip().startswith(_EMBED_DROP_PREFIXES)).strip() + "\n"


def strip_first_heading(text: str) -> str:
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if line.startswith("## "):
            return "\n".join(lines[:index] + lines[index + 1:]).strip()
        break
    return text


STAGE_ORDER = {"Qualification": 0, "Proposal": 1, "Negotiation": 2, "Closed Won": 3, "Closed Lost": 4}


def combine_labels(*labels: str) -> str:
    present = {label for label in labels if label}
    return "unknown" if not present else next(iter(present)) if len(present) == 1 else "mixed"


def latest(*dates: str) -> str:
    present = sorted(date for date in dates if date)
    return present[-1] if present else ""


def parse_money_k(text: str) -> int:
    cleaned = text.strip().lstrip("$").replace(",", "").lower()
    try:
        if cleaned.endswith("m"):
            return round(float(cleaned[:-1]) * 1000)
        if cleaned.endswith("k"):
            return round(float(cleaned[:-1]))
        return round(float(cleaned) / 1000)
    except ValueError:
        return 0


def parse_percent(text: str) -> float:
    try:
        return float(text.strip().rstrip("%")) / 100
    except ValueError:
        return 0.0


def format_money_k(thousands: int) -> str:
    return f"${thousands:,}k"


def render_composed_answer(title: str, conclusion: str, body_lines: list[str], citations: list[dict], confidence: str, freshness: str, as_of: str, next_action: str, access: str) -> str:
    lines = [f"# {title}", "", f"**Conclusion:** {conclusion}", "", *body_lines]
    freshness_line = f"**Confidence:** {confidence} | **Freshness:** {freshness}"
    if as_of:
        freshness_line += f" | **As of:** {as_of}"
    lines.append(freshness_line)
    sources = "; ".join(f"{item.get('boundary', '')}: {item.get('path') or item.get('handle') or 'restricted'}" for item in citations) or "none"
    lines.append(f"**Sources:** {sources}")
    if next_action:
        lines.append(f"**Next action:** {next_action}")
    lines.append(f"**Access:** {access}")
    return "\n".join(lines).rstrip() + "\n"
