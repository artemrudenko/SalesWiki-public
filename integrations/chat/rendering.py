"""Capability-aware plain Markdown chunking shared by chat adapters."""

from __future__ import annotations


def _hard_split(block: str, limit: int) -> list[str]:
    out: list[str] = []
    current: list[str] = []
    size = 0
    for line in block.split("\n"):
        while len(line) > limit:
            if current:
                out.append("\n".join(current))
                current, size = [], 0
            out.append(line[:limit])
            line = line[limit:]
        extra = len(line) + (1 if current else 0)
        if current and size + extra > limit:
            out.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + (1 if size else 0)
    if current:
        out.append("\n".join(current))
    return out


def split_markdown(text: str, limit: int) -> list[str]:
    """Split Markdown on line boundaries and keep normal code fences together."""
    if limit <= 0:
        raise ValueError("message length limit must be positive")
    if len(text) <= limit:
        return [text]
    blocks: list[str] = []
    current: list[str] = []
    fenced = False
    for line in text.split("\n"):
        current.append(line)
        if line.startswith("```"):
            fenced = not fenced
        if not fenced:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    expanded = [piece for block in blocks for piece in _hard_split(block, limit)]
    chunks: list[str] = []
    current_text = ""
    for block in expanded:
        candidate = block if not current_text else f"{current_text}\n{block}"
        if current_text and len(candidate) > limit:
            chunks.append(current_text)
            current_text = block
        else:
            current_text = candidate
    if current_text:
        chunks.append(current_text)
    return chunks
