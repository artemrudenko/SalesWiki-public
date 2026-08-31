"""Tests for scripts/build_dashboard_snapshots.py.

The snapshot links must resolve from the snapshot file's own location to the
real card in the vault. Historically the builder emitted vault-relative paths
verbatim, so a snapshot under demo/reports/dashboard-snapshots/ linked to
demo/reports/dashboard-snapshots/wiki/... while the cards live in
demo/demo-vault/wiki/... (the demo quickstart's first Obsidian click was broken).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "build_dashboard_snapshots.py"

LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class SnapshotLinkResolution(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="snap-links-"))
        # A vault and an output dir that are *siblings* under demo/, mirroring
        # the real layout: demo/demo-vault vs demo/reports/dashboard-snapshots.
        self.vault = self.tmp / "demo-vault"
        self.index = self.tmp / "indexes"
        self.output = self.tmp / "reports" / "dashboard-snapshots"
        card_rel = "wiki/entities/leads/Lead - Acme - Buyer.md"
        card = self.vault / card_rel
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text("# Lead\n", encoding="utf-8")
        self.card = card

        (self.index / "entities").mkdir(parents=True, exist_ok=True)
        (self.index / "freshness").mkdir(parents=True, exist_ok=True)
        row = {
            "entity_id": "demo-lead-acme-buyer",
            "type": "lead",
            "canonical_name": "Lead - Acme - Buyer",
            "path": card_rel,
            "owner": "demo-owner",
            "company": "Acme",
            "score": 90,
            "score_band": "hot",
        }
        (self.index / "entities" / "entities.jsonl").write_text(
            json.dumps(row) + "\n", encoding="utf-8"
        )
        (self.index / "freshness" / "freshness.jsonl").write_text("", encoding="utf-8")

    def _run(self) -> str:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--index-root",
                str(self.index),
                "--output-root",
                str(self.output),
                "--vault-root",
                str(self.vault),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return (self.output / "sales-today.md").read_text(encoding="utf-8")

    def test_link_resolves_to_the_real_card(self) -> None:
        text = self._run()
        targets = LINK.findall(text)
        self.assertTrue(targets, "snapshot must contain at least one card link")
        target = targets[0]
        resolved = (self.output / target).resolve()
        self.assertEqual(
            resolved,
            self.card.resolve(),
            f"link {target!r} from {self.output} must resolve to the card",
        )
        self.assertTrue(resolved.exists(), "linked card path must exist")


if __name__ == "__main__":
    unittest.main()
