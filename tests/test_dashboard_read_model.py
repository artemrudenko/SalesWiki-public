"""Tests for the policy-first dashboard projection and synthetic observations."""

from __future__ import annotations

import json
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


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class DashboardReadModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="dashboard-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.service = build_default_service(
            self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl", now=lambda: "t"
        )

    def test_sales_dashboard_uses_dated_observations_and_excludes_unowned_deals(self) -> None:
        result = self.service.dashboard(actor("demo-ivan-ae"))
        self.assertEqual((result["contract"], result["version"], result["history_status"]), ("saleswiki.dashboard-view", 1, "available"))
        self.assertTrue(result["synthetic"])
        names = {item["label"] for item in result["risk"]}
        self.assertIn("BluePeak Energy", names)
        self.assertNotIn("Northstar Robotics", names, "sales owner must not infer another team's commercial score")
        bluepeak = next(item for item in result["risk"] if item["label"] == "BluePeak Energy")
        self.assertEqual(bluepeak["history"], [61, 65, 69, 74])

    def test_marketing_gets_no_commercial_risk_or_secret(self) -> None:
        result = self.service.dashboard(actor("demo-nina-marketing"))
        self.assertEqual(result["risk"], [])
        payload = json.dumps(result)
        for secret in ("RivalCorp", "Discount floor", "ACV", "economic buyer"):
            self.assertNotIn(secret, payload)

    def test_one_observation_is_honestly_insufficient(self) -> None:
        observations = self.vault / "state" / "dashboard-observations.jsonl"
        first = observations.read_text(encoding="utf-8").splitlines()[0]
        observations.write_text(first + "\n", encoding="utf-8")
        result = self.service.dashboard(actor("demo-ivan-ae"))
        self.assertEqual(result["history_status"], "insufficient-history")
        self.assertEqual(result["risk"], [])


if __name__ == "__main__":
    unittest.main()
