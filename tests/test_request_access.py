"""request_access proposal type: chat users can request access to a restricted
source; it lands in the curator review queue as a first-class typed proposal and,
once approved, the single-writer worker records it on the card's Review Needed
section (audit chain stays intact). Mirrors the governance pattern of the existing
flag_stale_or_wrong / request_redaction_review types.
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
from saleswiki_mcp import config, worker  # noqa: E402
from saleswiki_mcp.audit import verify_chain  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

COMPANY_ID = "demo-company-bluepeak-energy"
CARD = Path("broad") / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"


class RequestAccessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="req-access-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.audit = self.tmp / "audit.jsonl"
        self.proposals = self.tmp / "proposals.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(
            self.vault, self.audit, self.proposals, now=lambda: "2026-06-14T00:00:00Z"
        )

    def who(self, actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def test_any_role_can_request_access_and_curator_sees_typed_proposal(self) -> None:
        pid = self.svc.request_access(
            self.who("demo-broad-viewer"), COMPANY_ID, "need personal-data for discovery"
        )
        self.assertTrue(pid)
        queue = self.svc.review_queue(self.who("demo-sophie-curator"))
        self.assertEqual(queue["access"], "allowed")
        match = [i for i in queue["items"] if i.get("proposal_id") == pid]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["type"], "request_access")
        self.assertEqual(match[0]["requester"], "demo-broad-viewer")

    def test_approved_request_is_recorded_by_worker_and_audit_intact(self) -> None:
        pid = self.svc.request_access(
            self.who("demo-broad-viewer"), COMPANY_ID, "need discovery notes"
        )
        approved = self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)
        self.assertEqual(approved["status"], "approved")
        summary = worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "2026-06-14T01:00:00Z",
        )
        self.assertIn(pid, summary["applied"])
        body = (self.vault / CARD).read_text(encoding="utf-8")
        self.assertIn("Access requested", body)
        self.assertTrue(verify_chain(self.audit))


if __name__ == "__main__":
    unittest.main()
