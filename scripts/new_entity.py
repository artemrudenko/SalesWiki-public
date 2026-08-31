#!/usr/bin/env python3
"""Canonical entity creation - the single chokepoint that mints an id and writes
a card from its template, per wiki/processes/identifier-strategy.md.

Instead of hand-authoring `entity_id`, create entities through this tool: it mints
an opaque, rename-safe, time-sortable id (`<type>_<ULID>`) via the IdAllocator
ledger (idempotent by natural key, so re-running for the same real object reuses
its id), instantiates the matching `_template.md`, and writes the card with a
readable `slug` alongside the id.

Usage:
    python3 scripts/new_entity.py --type company --name "Acme Corp" --natural-key acme.com
    python3 scripts/new_entity.py --type lead --name "Acme - Primary Buyer" --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp.ids import IdAllocator  # noqa: E402

DEFAULT_LEDGER = ROOT / "state" / "id-ledger.jsonl"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _templates(vault_root: Path) -> dict[str, Path]:
    """Map card type -> its _template.md path under <vault>/wiki/entities/*/."""
    out: dict[str, Path] = {}
    for tmpl in sorted((vault_root / "wiki" / "entities").glob("*/_template.md")):
        for line in tmpl.read_text(encoding="utf-8").splitlines():
            if line.startswith("type:"):
                out[line.split(":", 1)[1].strip()] = tmpl
                break
    return out


def _heading_label(template_text: str) -> str:
    """The title prefix from a template heading like `# Company: <Name>` -> Company."""
    m = re.search(r"^# *([^:<#\n]+?) *:", template_text, re.MULTILINE)
    return m.group(1).strip() if m else "Entity"


def create_entity(
    card_type: str,
    name: str,
    *,
    vault_root: Path,
    ledger_path: Path,
    natural_key: str = "",
    slug: str | None = None,
    today: str | None = None,
    allocator: IdAllocator | None = None,
) -> dict:
    """Mint an id and write a new entity card from its template. Idempotent by
    natural key: if one was already minted, that id (and existing card) is reused.
    """
    templates = _templates(vault_root)
    if card_type not in templates:
        raise ValueError(f"no template for type {card_type!r} (known: {sorted(templates)})")
    tmpl_path = templates[card_type]
    template_text = tmpl_path.read_text(encoding="utf-8")
    label = _heading_label(template_text)
    slug = slug or slugify(name)
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    alloc = allocator or IdAllocator(ledger_path)
    entity_id = alloc.mint(card_type, natural_key)

    folder = tmpl_path.parent
    path = folder / f"{label} - {name}.md"
    created = not path.exists()
    if created:
        text = template_text
        text = re.sub(r"^entity_id:.*$", f"entity_id: {entity_id}", text, count=1, flags=re.MULTILINE)
        if "\nslug:" not in text:
            text = re.sub(r"^(entity_id:.*)$", rf"\1\nslug: {slug}", text, count=1, flags=re.MULTILINE)
        for field in ("created", "updated", "last_reviewed"):
            text = re.sub(rf"^{field}:.*$", f"{field}: {today}", text, count=1, flags=re.MULTILINE)
        text = text.replace("<Name>", name)
        path.write_text(text, encoding="utf-8")

    return {"entity_id": entity_id, "slug": slug, "path": str(path), "created": created, "label": label}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an entity card with a minted id.")
    parser.add_argument("--type", required=True, help="card type, e.g. company, lead, deal")
    parser.add_argument("--name", required=True, help="display name")
    parser.add_argument("--natural-key", default="", help="dedup key (domain, email, CRM id)")
    parser.add_argument("--slug", default=None, help="readable slug (default: from name)")
    parser.add_argument("--vault-root", default=str(ROOT), help="vault root containing wiki/entities")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="id ledger path")
    parser.add_argument("--dry-run", action="store_true", help="mint + report without writing the card")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[dry-run] would create {args.type} '{args.name}' (slug {args.slug or slugify(args.name)}); id minted as {args.type}_<ULID> on a real run")
        return 0
    result = create_entity(
        args.type, args.name,
        vault_root=Path(args.vault_root), ledger_path=Path(args.ledger),
        natural_key=args.natural_key, slug=args.slug,
    )
    action = "created" if result["created"] else "exists (reused id)"
    print(f"{action}: {result['entity_id']} -> {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
