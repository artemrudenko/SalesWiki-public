"""Approval actually grants access. An approved request_access proposal becomes a
live, scoped grant: the same requester role that was blocked now reads exactly the
granted company's sales-confidential data (and nothing else). A merely-requested or
rejected proposal grants nothing. This is the "approve = grant" half of the loop.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

COMPANY_ID = "demo-company-bluepeak-energy"


class GrantAccessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="grant-access-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.svc = build_default_service(
            self.vault, self.tmp / "audit.jsonl", self.tmp / "proposals.jsonl",
            now=lambda: "2026-06-14T00:00:00Z",
        )

    def who(self, actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def deal_access(self, actor_id: str, company: str) -> str:
        return self.svc.deal_risk(self.who(actor_id), company)["access"]

    def test_approved_request_grants_scoped_read(self) -> None:
        # Before: a viewer is blocked from BluePeak's deal risk.
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")
        before_graph = self.svc.entity_graph(self.who("demo-broad-viewer"), "BluePeak Energy")
        self.assertNotIn("deal", {node["type"] for node in before_graph["nodes"]})
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need deal risk")
        self.assertEqual(
            self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)["status"], "approved"
        )
        # After: same viewer role now reads BluePeak's deal risk...
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "allowed")
        after_graph = self.svc.entity_graph(self.who("demo-broad-viewer"), "BluePeak Energy")
        self.assertIn("deal", {node["type"] for node in after_graph["nodes"]})
        # ...but the grant is scoped to BluePeak only — Atlas stays blocked.
        self.assertEqual(self.deal_access("demo-broad-viewer", "Atlas Foods"), "blocked")

    def test_request_without_approval_grants_nothing(self) -> None:
        self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "pending")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")

    def test_rejected_request_grants_nothing(self) -> None:
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "x")
        self.svc.reject_proposal(self.who("demo-sophie-curator"), pid, "not now")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")


if __name__ == "__main__":
    unittest.main()
