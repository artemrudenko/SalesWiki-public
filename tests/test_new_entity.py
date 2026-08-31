"""Adoption tests: the entity-creation chokepoint mints ids and writes cards.

create_entity is the single place a production entity card is born: it mints a
typed ULID id (idempotent by natural key), writes the card from its template with
the id + a readable slug, and uses the template's heading for the filename.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import new_entity  # noqa: E402
from saleswiki_mcp.ids import IdAllocator  # noqa: E402


class CreateEntity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="newent-"))
        # Minimal vault with the real company + lead templates.
        for folder in ("companies", "leads"):
            dst = self.tmp / "wiki" / "entities" / folder
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "wiki" / "entities" / folder / "_template.md", dst / "_template.md")
        self.ledger = self.tmp / "id-ledger.jsonl"

    def _create(self, ctype, name, **kw):
        return new_entity.create_entity(ctype, name, vault_root=self.tmp, ledger_path=self.ledger, today="2026-06-04", **kw)

    def test_creates_card_with_minted_id_and_slug(self) -> None:
        r = self._create("company", "Acme Corp", natural_key="acme.example")
        self.assertTrue(r["entity_id"].startswith("company_"))
        card = Path(r["path"])
        self.assertTrue(card.exists())
        text = card.read_text(encoding="utf-8")
        self.assertIn(f"entity_id: {r['entity_id']}", text)
        self.assertIn("slug: acme-corp", text)
        self.assertIn("created: 2026-06-04", text)
        self.assertIn("Acme Corp", text)
        self.assertNotIn("<Name>", text)
        self.assertEqual(card.name, "Company - Acme Corp.md")

    def test_idempotent_by_natural_key(self) -> None:
        a = self._create("company", "Acme Corp", natural_key="acme.example")
        b = self._create("company", "Acme Corp", natural_key="acme.example")
        self.assertEqual(a["entity_id"], b["entity_id"], "same natural key reuses the id")
        self.assertFalse(b["created"], "card already exists; not overwritten")

    def test_distinct_entities_get_distinct_ids(self) -> None:
        a = self._create("company", "Acme Corp", natural_key="acme.example")
        b = self._create("company", "Globex", natural_key="globex.example")
        self.assertNotEqual(a["entity_id"], b["entity_id"])

    def test_unknown_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._create("nonexistent-type", "X")

    def test_ledger_records_the_mint(self) -> None:
        self._create("lead", "Acme - Primary Buyer", natural_key="acme-lead")
        ids = [r["id"] for r in IdAllocator(self.ledger).records()]
        self.assertTrue(any(i.startswith("lead_") for i in ids))


if __name__ == "__main__":
    unittest.main()
