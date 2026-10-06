"""The Answer Contract: one envelope every read tool fills, plus a renderer.

The core never generates prose - it extracts cited values from cards. This module
gives that output a single, predictable shape (structured fields + rendered
Markdown) with readable tables for record lists, mandatory provenance, and an
honest "missing" state when the vault has no data.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Citation:
    boundary: str
    path: str = ""
    handle: str = ""

    def as_dict(self) -> dict:
        d: dict = {"boundary": self.boundary}
        if self.path:
            d["path"] = self.path
        if self.handle:
            d["handle"] = self.handle
        return d

    def render(self) -> str:
        return f"{self.boundary}: {self.path or self.handle or 'restricted'}"


@dataclass(frozen=True)
class Table:
    columns: list[str]
    rows: list[list[str]]

    def as_dict(self) -> dict:
        return {"columns": list(self.columns), "rows": [list(r) for r in self.rows]}


@dataclass
class Section:
    heading: str
    bullets: list[str] = field(default_factory=list)
    table: Table | None = None

    def as_dict(self) -> dict:
        d: dict = {"heading": self.heading, "bullets": list(self.bullets)}
        if self.table is not None:
            d["table"] = self.table.as_dict()
        return d


@dataclass
class Answer:
    title: str
    access: str  # allowed | sanitized | aggregated | blocked | not-found | ambiguous
    conclusion: str
    sections: list[Section] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    restricted: list[str] = field(default_factory=list)
    confidence: str = "medium"
    freshness: str = "unknown"
    as_of: str = ""
    next_action: str = ""
    missing: list[str] = field(default_factory=list)
    redaction_notice: str = ""

    @classmethod
    def not_found(cls, title: str, missing_line: str, next_action: str = "") -> "Answer":
        """Honest 'I don't know': no data, an explicit Missing note, no filler."""
        return cls(
            title=title,
            access="not-found",
            conclusion="Cannot answer from the knowledge base.",
            missing=[missing_line],
            next_action=next_action,
        )

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "access": self.access,
            "conclusion": self.conclusion,
            "sections": [s.as_dict() for s in self.sections],
            "citations": [c.as_dict() for c in self.citations],
            "restricted": list(self.restricted),
            "confidence": self.confidence,
            "freshness": self.freshness,
            "as_of": self.as_of,
            "next_action": self.next_action,
            "missing": list(self.missing),
            "redaction_notice": self.redaction_notice,
            "text": render(self),
        }


def _cell(value: str) -> str:
    """Make a value safe for a Markdown table cell."""
    return str(value).replace("\n", " ").replace("|", "\\|").strip()


def markdown_table(columns: list[str], rows: list[list[str]]) -> list[str]:
    """Render a Markdown table as a list of lines."""
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        out.append("| " + " | ".join(_cell(c) for c in row) + " |")
    return out


def render(answer: Answer) -> str:
    """Render an Answer to standardized Markdown."""
    lines = [f"# {answer.title}", "", f"**Conclusion:** {answer.conclusion}", ""]
    for section in answer.sections:
        lines.append(f"## {section.heading}")
        if section.table is not None:
            lines += markdown_table(section.table.columns, section.table.rows)
        lines += [f"- {b}" for b in section.bullets]
        lines.append("")
    if answer.restricted:
        lines.append("## Restricted For Your Role")
        lines += [f"- {r}" for r in answer.restricted]
        lines.append("")
    if answer.missing:
        lines.append("## Missing")
        lines += [f"- {m}" for m in answer.missing]
        lines.append("")
    freshness_line = f"**Confidence:** {answer.confidence} | **Freshness:** {answer.freshness}"
    if answer.as_of:
        freshness_line += f" | **As of:** {answer.as_of}"
    lines.append(freshness_line)
    sources = "; ".join(c.render() for c in answer.citations) if answer.citations else "none"
    lines.append(f"**Sources:** {sources}")
    if answer.next_action:
        lines.append(f"**Next action:** {answer.next_action}")
    if answer.redaction_notice:
        lines.append(f"**Redaction:** {answer.redaction_notice}")
    lines.append(f"**Access:** {answer.access}")
    return "\n".join(lines) + "\n"
