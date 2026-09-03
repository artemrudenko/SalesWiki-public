"""Slice 5 tests: a second proposal type + worker type dispatch.

request_redaction_review proves the propose/approve/apply loop is not tied to a
single proposal type: the worker dispatches by proposal type to a handler, and an
unknown type is refused (failed) rather than applied.
Run with: python3 -m unittest discover -s tests
"""

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
from saleswiki_mcp import config, worker  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.proposals import ProposalStore, content_hash, payload_hash  # noqa: E402
from saleswiki_mcp.retrieval import Retriever  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

TARGET = "demo-company-bluepeak-energy"


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class RedactionAndDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="redaction-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.proposals = self.tmp / "proposals.jsonl"
        self.audit = self.tmp / "audit.jsonl"
        self.runtime = self.tmp / "runtime"
        self.svc = build_default_service(self.vault, self.audit, self.proposals, now=lambda: "t")
        self.card = self.vault / "broad" / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"

    def _run(self):
        return worker.apply_approved(self.vault, self.proposals, self.audit, self.runtime, now=lambda: "t2")

    def test_redaction_proposal_is_drafted_with_hash(self) -> None:
        pid = self.svc.request_redaction_review(actor("demo-olivia-marketing"), TARGET, "contact PII may be exposed")
        state = self.svc.proposal_state(pid)
        self.assertEqual(state["type"], "request_redaction_review")
        self.assertEqual(state["status"], "draft")
        self.assertTrue(state.get("payload_hash"))

    def test_approved_redaction_applies_with_redaction_note(self) -> None:
        pid = self.svc.request_redaction_review(actor("demo-olivia-marketing"), TARGET, "contact PII may be exposed")
        self.svc.approve_proposal(actor("demo-sophie-curator"), pid)
        summary = self._run()
        self.assertIn(pid, summary["applied"])
        text = self.card.read_text(encoding="utf-8")
        self.assertIn("Redaction review", text)
        self.assertIn("contact PII may be exposed", text)

    def test_unknown_proposal_type_is_refused(self) -> None:
        store = ProposalStore(self.proposals)
        body = content_hash(Retriever(self.vault, config.boundary_registry()).find(TARGET).body)
        pid = store.append({
            "type": "bogus_type", "status": "draft", "target": TARGET, "note": "x",
            "payload_hash": payload_hash("bogus_type", TARGET, "x"), "base_hash": body,
        })
        self.svc.approve_proposal(actor("demo-sophie-curator"), pid)
        before = self.card.read_bytes()
        summary = self._run()
        self.assertEqual(summary["applied"], [])
        self.assertTrue(any(f["proposal_id"] == pid for f in summary["failed"]))
        self.assertEqual(self.card.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
