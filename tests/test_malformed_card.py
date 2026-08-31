"""Read-path resilience to malformed cards (review L5).

A card with broken / unterminated YAML frontmatter must degrade gracefully: the
parser never throws, the Retriever still loads the vault, and — critically — a
corrupt card under a restricted folder keeps its restricted boundary (resolved
from the path, not the frontmatter), so a broken card can never silently become
world-readable.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from saleswiki_mcp import config, frontmatter
from saleswiki_mcp.retrieval import Retriever


class MalformedFrontmatter(unittest.TestCase):
    def test_parser_never_throws(self) -> None:
        for text in (
            "---\nbroken: [unclosed\nno closing fence",   # no terminating ---
            "---\n\tjunk\n: : :\n---\nbody",               # garbage inside fences
            "---\n---\n",                                   # empty frontmatter
            "no frontmatter at all",
        ):
            props, body = frontmatter.parse(text)
            self.assertIsInstance(props, dict)
            self.assertIsInstance(body, str)

    def test_retriever_loads_vault_with_a_corrupt_card(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="malformed-"))
        good = tmp / "broad" / "wiki" / "entities" / "companies"
        good.mkdir(parents=True)
        (good / "Company - Ok.md").write_text(
            "---\ntype: company\nentity_id: demo-company-ok\n---\n\nbody\n", encoding="utf-8")
        bad = tmp / "sales-confidential" / "wiki" / "entities" / "deals"
        bad.mkdir(parents=True)
        corrupt = bad / "Deal - Corrupt.md"
        corrupt.write_text("---\nthis: [is, broken\nno closing fence\nSecret floor 12%", encoding="utf-8")

        retriever = Retriever(tmp, config.boundary_registry())
        cards = retriever.cards()  # must not raise
        self.assertTrue(retriever.find("demo-company-ok"), "the good card still resolves")

        corrupt_card = next(c for c in cards if c.title == "Deal - Corrupt")
        self.assertEqual(
            corrupt_card.boundary, "sales-confidential",
            "a corrupt card keeps its path-derived restricted boundary, never degrading to broad",
        )


if __name__ == "__main__":
    unittest.main()
