"""Retriever cache invalidation.

`Retriever.cards()` used to cache the parsed vault forever, so a long-running
in-process service (the Rocket.Chat bridge in default mode) kept answering from
stale cards after the worker applied an approved proposal to disk. The cache
must stay a cache (no re-parse when nothing changed) but reload when a card is
edited, added or deleted under the vault root.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from saleswiki_mcp import config
from saleswiki_mcp.retrieval import Retriever

CARD = "---\ntype: company\nentity_id: demo-company-ok\n---\n\n## Review Needed\n\n- (none)\n"


class RetrieverCacheInvalidation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="retr-cache-"))
        self.companies = self.tmp / "broad" / "wiki" / "entities" / "companies"
        self.companies.mkdir(parents=True)
        self.card_path = self.companies / "Company - Ok.md"
        self.card_path.write_text(CARD, encoding="utf-8")
        self.retriever = Retriever(self.tmp, config.boundary_registry())

    def test_cache_is_reused_when_vault_unchanged(self) -> None:
        self.assertIs(
            self.retriever.cards(), self.retriever.cards(),
            "an unchanged vault must not be re-parsed on every call",
        )

    def test_worker_style_edit_is_picked_up(self) -> None:
        self.assertNotIn("flagged as stale", self.retriever.find("demo-company-ok").body)
        # The worker appends a Review Needed bullet via an atomic rewrite.
        self.card_path.write_text(
            CARD.replace("- (none)", "- flagged as stale by demo-broad-viewer"), encoding="utf-8")
        self.assertIn(
            "flagged as stale", self.retriever.find("demo-company-ok").body,
            "a card edited on disk must be re-read, not served from the stale cache",
        )

    def test_same_size_edit_with_newer_mtime_is_picked_up(self) -> None:
        self.retriever.cards()
        edited = CARD.replace("- (none)", "- (done)")
        self.assertEqual(len(edited.encode("utf-8")), len(CARD.encode("utf-8")))
        self.card_path.write_text(edited, encoding="utf-8")
        # Force a visibly newer mtime so the test does not depend on fs tick granularity.
        st = self.card_path.stat()
        os.utime(self.card_path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        self.assertIn("- (done)", self.retriever.find("demo-company-ok").body)

    def test_added_and_deleted_cards_are_picked_up(self) -> None:
        self.assertIsNone(self.retriever.find("demo-company-new"))
        new_path = self.companies / "Company - New.md"
        new_path.write_text(
            "---\ntype: company\nentity_id: demo-company-new\n---\n\nbody\n", encoding="utf-8")
        self.assertIsNotNone(
            self.retriever.find("demo-company-new"), "a card created on disk must appear")
        new_path.unlink()
        self.assertIsNone(
            self.retriever.find("demo-company-new"), "a card deleted on disk must disappear")


if __name__ == "__main__":
    unittest.main()
