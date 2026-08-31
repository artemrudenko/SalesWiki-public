"""Machine-readable vendor-first connector decision contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConnectorStrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "schemas" / "connector-contracts.json").read_text(encoding="utf-8")
        )

    def test_vendor_first_order_keeps_custom_code_last(self) -> None:
        order = self.contract["selection_policy"]["preference_order"]
        self.assertEqual(order[0], "official-vendor-mcp")
        self.assertEqual(order[-1], "custom-thin-adapter")

    def test_external_writes_keep_the_governed_boundary(self) -> None:
        self.assertEqual(
            self.contract["selection_policy"]["external_write_boundary"],
            "proposal-approval-worker-action-audit",
        )

    def test_planned_vendor_connectors_declare_strategy_and_official_sources(self) -> None:
        connectors = self.contract["connectors"]
        for name in ("hubspot", "google-drive-meet", "slack-or-email-digest"):
            strategy = connectors[name]["implementation_strategy"]
            urls = [
                value
                for value in strategy.values()
                if isinstance(value, str) and value.startswith("https://")
            ]
            urls.extend(strategy.get("official_references", []))
            self.assertTrue(urls, f"{name} needs an official capability reference")


if __name__ == "__main__":
    unittest.main()
