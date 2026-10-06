"""End-to-end integration test: the full governed lifecycle across roles.

Drives the MCP-bound tool handlers (server.build_tools) and the single-writer
worker over one shared vault + proposal store, exercising:
read-contrast -> propose -> review -> approve -> apply -> rollback, plus a reject
path. This is the one scenario test that proves the slices compose correctly.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config, server, worker  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

SALES_SECRETS = ("Discount floor", "Pricing:", "ACV")


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class EndToEndLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="e2e-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.proposals = self.tmp / "proposals.jsonl"
        self.audit = self.tmp / "audit.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(self.vault, self.audit, self.proposals, now=lambda: "t")
        self.tools = {who: server.build_tools(self.svc, actor(who)) for who in (
            "demo-olivia-marketing", "demo-ethan-ae", "demo-sophie-curator", "demo-raj-revops",
        )}
        self.card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"

    def test_full_governed_lifecycle(self) -> None:
        # 1. Read-contrast through the gateway tools.
        olivia = self.tools["demo-olivia-marketing"]
        ethan = self.tools["demo-ethan-ae"]
        self.assertTrue(any(s in ethan["saleswiki.company_brief"]("BluePeak Energy")["text"] for s in SALES_SECRETS))
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, olivia["saleswiki.company_brief"]("BluePeak Energy")["text"])

        # 2. Marketing proposes a redaction review.
        msg = olivia["saleswiki.request_redaction_review"]("demo-company-bluepeak-energy", "contact PII exposed")
        self.assertIn("proposal-", msg["text"])
        pid = "proposal-0001"

        # 3. Curator sees it in the queue; a sales role cannot approve.
        self.assertIn(pid, self.tools["demo-sophie-curator"]["saleswiki.review_queue"]("")["text"])
        self.assertIn("not", ethan["saleswiki.approve_proposal"](pid)["text"].lower())
        # RevOps can inspect but not approve.
        self.assertIn(pid, self.tools["demo-raj-revops"]["saleswiki.review_queue"]("")["text"])

        # 4. Curator approves; production is still unchanged until the worker runs.
        self.assertIn("approved", self.tools["demo-sophie-curator"]["saleswiki.approve_proposal"](pid)["text"].lower())
        self.assertNotIn("contact PII exposed", self.card.read_text(encoding="utf-8"))

        # 5. Single-writer worker applies it.
        summary = worker.apply_approved(self.vault, self.proposals, self.audit, self.runtime, now=lambda: "t2")
        self.assertIn(pid, summary["applied"])
        self.assertIn("contact PII exposed", self.card.read_text(encoding="utf-8"))

        # 6. Rollback restores the card.
        worker.rollback(self.vault, self.proposals, self.audit, self.runtime, pid, now=lambda: "t3")
        self.assertNotIn("contact PII exposed", self.card.read_text(encoding="utf-8"))
        self.assertEqual(self.svc.proposal_state(pid)["status"], "rolled-back")

    def test_reject_path_never_applies(self) -> None:
        self.tools["demo-ethan-ae"]["saleswiki.flag_stale_or_wrong"]("demo-company-bluepeak-energy", "stale")
        pid = "proposal-0001"
        self.assertIn("rejected", self.tools["demo-sophie-curator"]["saleswiki.reject_proposal"](pid, "no")["text"].lower())
        summary = worker.apply_approved(self.vault, self.proposals, self.audit, self.runtime, now=lambda: "t2")
        self.assertNotIn(pid, summary["applied"])


if __name__ == "__main__":
    unittest.main()
