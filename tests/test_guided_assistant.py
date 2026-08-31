"""Guided assistant must be a fixed, policy-filtered routing layer."""

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
from saleswiki_mcp.server import build_tools  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class GuidedAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="guided-"))
        vault = tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        self.service = build_default_service(vault, tmp / "audit.jsonl", tmp / "proposals.jsonl", now=lambda: "t")

    def test_allowlisted_prompt_routes_to_a_cited_answer(self) -> None:
        out = self.service.guided_answer(actor("demo-ivan-ae"), "call_prep", "BluePeak Energy")
        self.assertEqual(out["intent"], "call_prep")
        self.assertIn("Call Prep", out["title"])
        self.assertTrue(out["citations"])

    def test_marketing_cannot_get_commercial_detail_through_guided_route(self) -> None:
        out = self.service.guided_answer(actor("demo-nina-marketing"), "deal_risk", "BluePeak Energy")
        payload = json.dumps(out)
        self.assertEqual(out["access"], "blocked")
        self.assertNotIn("Discount floor", payload)
        self.assertNotIn("RivalCorp", payload)

    def test_route_does_not_accept_client_selected_tool_name(self) -> None:
        with self.assertRaises(ValueError):
            self.service.guided_answer(actor("demo-ivan-ae"), "saleswiki.pipeline_risk_digest", "BluePeak Energy")
        tools = build_tools(self.service, actor("demo-ivan-ae"))
        self.assertIn("saleswiki.guided_answer", tools)


if __name__ == "__main__":
    unittest.main()
