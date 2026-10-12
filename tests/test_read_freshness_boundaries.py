"""Answer metadata must come from role-visible, cited records only."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402


class ReadFreshnessBoundaries(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="read-freshness-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = self.root / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.service = build_default_service(
            self.vault, self.root / "audit.jsonl", self.root / "proposals.jsonl",
            now=lambda: "2026-06-03T00:00:00Z",
        )
        self.marketing = FixtureIdentityProvider(
            "demo-olivia-marketing", config.identity_config(),
        ).resolve()

    def test_blocked_lead_cannot_change_answer_metadata(self) -> None:
        before = self.service.lead_priority(self.marketing)
        source = next(self.vault.rglob("Lead - BluePeak Energy*.md"))
        quarantine = self.vault / "quarantine"
        quarantine.mkdir()
        hidden = source.read_text(encoding="utf-8").replace(
            "freshness: fresh", "freshness: stale",
        )
        hidden = re.sub(r"(?m)^updated:.*$", "updated: 2099-01-01", hidden)
        (quarantine / "Lead - Hidden synthetic record.md").write_text(hidden, encoding="utf-8")

        after = self.service.lead_priority(self.marketing)

        self.assertEqual(after, before, "blocked records must not change text or answer metadata")

    def test_visible_stale_deal_marks_risk_as_recorded_without_lowering_lead_band(self) -> None:
        owner = FixtureIdentityProvider("demo-ethan-ae", config.identity_config()).resolve()
        marketing_before = self.service.lead_priority(self.marketing, "BluePeak Energy")
        owner_before = self.service.lead_priority(owner, "BluePeak Energy")
        path = next(self.vault.rglob("Deal - BluePeak Energy*.md"))
        text = path.read_text(encoding="utf-8").replace("freshness: fresh", "freshness: stale")
        text = re.sub(r"(?m)^updated:.*$", "updated: 2025-01-01", text)
        path.write_text(text, encoding="utf-8")

        owner_after = self.service.lead_priority(owner, "BluePeak Energy")
        row = owner_after["sections"][0]["table"]["rows"][0]

        self.assertEqual(row[2], owner_before["sections"][0]["table"]["rows"][0][2])
        self.assertEqual(owner_after["freshness"], "mixed")
        self.assertIn("Last recorded risk", row[6])
        self.assertIn("2025-01-01", row[6])
        self.assertIn("Verify current linked-deal context", row[5])
        self.assertIn("1 need current-context review", owner_after["conclusion"])
        self.assertEqual(self.service.lead_priority(self.marketing, "BluePeak Energy"), marketing_before)

    def test_blocked_pain_cannot_change_content_answer_metadata(self) -> None:
        before = self.service.content_opportunities(self.marketing)
        source = next(self.vault.rglob("Pain Point - *.md"))
        quarantine = self.vault / "quarantine"
        quarantine.mkdir()
        hidden = source.read_text(encoding="utf-8").replace(
            "freshness: fresh", "freshness: stale",
        )
        hidden = re.sub(r"(?m)^updated:.*$", "updated: 2099-01-01", hidden)
        (quarantine / "Pain Point - Hidden synthetic record.md").write_text(hidden, encoding="utf-8")

        after = self.service.content_opportunities(self.marketing)

        self.assertEqual(after, before, "blocked records must not change text or answer metadata")

    def test_unknown_linked_deal_freshness_requests_review(self) -> None:
        owner = FixtureIdentityProvider("demo-ethan-ae", config.identity_config()).resolve()
        path = next(self.vault.rglob("Deal - BluePeak Energy*.md"))
        path.write_text(path.read_text(encoding="utf-8").replace(
            "freshness: fresh", "freshness: unknown",
        ), encoding="utf-8")

        out = self.service.lead_priority(owner, "BluePeak Energy")
        row = out["sections"][0]["table"]["rows"][0]

        self.assertEqual(out["freshness"], "mixed")
        self.assertIn("freshness not established", row[6])
        self.assertIn("Verify current linked-deal context", row[5])
        self.assertEqual(row[2], "hot")

    def test_empty_visible_pool_has_no_hidden_freshness_or_date(self) -> None:
        quarantine = self.vault / "quarantine"
        quarantine.mkdir()
        for pattern in ("Lead - *.md", "Pain Point - *.md"):
            for path in self.vault.rglob(pattern):
                if path.parent != quarantine:
                    path.rename(quarantine / path.name)

        for tool in (self.service.lead_priority, self.service.content_opportunities):
            with self.subTest(tool=tool.__name__):
                out = tool(self.marketing)
                self.assertEqual(out["freshness"], "unknown")
                self.assertEqual(out["as_of"], "")
                self.assertEqual(out["citations"], [])
                self.assertEqual(out["sections"][0]["table"]["rows"], [])


if __name__ == "__main__":
    unittest.main()
