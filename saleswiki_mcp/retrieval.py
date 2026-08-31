"""Load and look up cards from a boundary vault root over generated/demo content."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import frontmatter
from .boundaries import resolve_boundary


def card_text(card: "Card") -> str:
    """Lowercased searchable text for substring matching (title + entity_id)."""
    return f"{card.title} {card.entity_id}".lower()


@dataclass(frozen=True)
class Card:
    rel_path: str
    boundary: str
    entity_id: str
    type: str
    title: str
    owner: str
    team: str
    company: str
    access: str
    body: str
    freshness: str = ""
    updated: str = ""

    @property
    def display(self) -> str:
        for prefix in ("Company - ", "Deal - ", "Lead - ", "Event - ", "Call - ", "Campaign - ", "Pain Point - ", "Personal-Data Ref - "):
            if self.title.startswith(prefix):
                return self.title[len(prefix):]
        return self.title


class Retriever:
    def __init__(self, vault_root: Path, registry: dict) -> None:
        self._root = Path(vault_root)
        self._registry = registry
        self._cards: list[Card] | None = None
        self._signature: tuple[tuple[str, int, int], ...] | None = None

    def _load(self) -> list[Card]:
        cards: list[Card] = []
        for path in sorted(self._root.rglob("*.md")):
            rel = path.relative_to(self._root).as_posix()
            props, body = frontmatter.parse(path.read_text(encoding="utf-8"))
            cards.append(
                Card(
                    rel_path=rel,
                    boundary=resolve_boundary(rel, self._registry),
                    entity_id=props.get("entity_id", ""),
                    type=props.get("type", ""),
                    title=path.stem,
                    owner=props.get("owner", ""),
                    team=props.get("team", ""),
                    company=props.get("company", ""),
                    access=props.get("access", ""),
                    body=body,
                    freshness=props.get("freshness", ""),
                    updated=props.get("updated", ""),
                )
            )
        return cards

    def _vault_signature(self) -> tuple[tuple[str, int, int], ...]:
        """Stat-only change detector: every card path with mtime and size. Far
        cheaper than re-parsing, and catches edits, adds and deletes anywhere
        under the root (the root directory's own mtime would miss nested edits)."""
        signature: list[tuple[str, int, int]] = []
        for path in sorted(self._root.rglob("*.md")):
            try:
                st = path.stat()
            except OSError:  # deleted between rglob and stat — next call settles it
                continue
            signature.append((path.relative_to(self._root).as_posix(), st.st_mtime_ns, st.st_size))
        return tuple(signature)

    def cards(self) -> list[Card]:
        # Reload when the vault changed on disk, so a long-running service sees
        # worker-applied edits instead of a stale cache. Signature is taken
        # BEFORE the load: a write racing the load can only cause one extra
        # reload later, never a stale hit.
        signature = self._vault_signature()
        if self._cards is None or signature != self._signature:
            self._cards = self._load()
            self._signature = signature
        return self._cards

    def find(self, query: str, card_type: str | None = None) -> Card | None:
        """Resolve a query to a single card, conservatively. An exact entity_id or
        display match wins, but only when it is unique: a display like "Atlas Foods"
        collides across a Company, Lead and Personal-Data Ref, so an unscoped exact
        match with >1 hit returns None (fail closed) rather than silently picking the
        first-sorted card. Otherwise a substring match is accepted only when unique.
        The caller surfaces the candidates instead of briefing the wrong entity.
        """
        q = query.strip().lower()
        pool = [c for c in self.cards() if card_type is None or c.type == card_type]
        exact = [c for c in pool if c.entity_id.lower() == q or c.display.lower() == q]
        if exact:
            return exact[0] if len(exact) == 1 else None
        substring = [c for c in pool if q and q in card_text(c)]
        return substring[0] if len(substring) == 1 else None

    def candidates(self, query: str, card_type: str | None = None) -> list[Card]:
        """All cards a query could refer to (exact wins; else substring matches)."""
        q = query.strip().lower()
        pool = [c for c in self.cards() if card_type is None or c.type == card_type]
        exact = [c for c in pool if c.entity_id.lower() == q or c.display.lower() == q]
        if exact:
            return exact
        return [c for c in pool if q and q in card_text(c)]

    def find_company(self, query: str) -> Card | None:
        return self.find(query, "company")

    def related(self, company_entity_id: str) -> list[Card]:
        return [c for c in self.cards() if c.company == company_entity_id]

    def by_type(self, card_type: str) -> list[Card]:
        return [c for c in self.cards() if c.type == card_type]

    def related_by_type(self, company_entity_id: str, card_type: str) -> list[Card]:
        return [c for c in self.cards() if c.company == company_entity_id and c.type == card_type]
