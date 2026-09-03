"""Regression locks for core permissioned-knowledge hardening fixes.

Each test pins a concrete security or correctness invariant that was RED before
its fix.
"""

from __future__ import annotations

import json
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config, worker  # noqa: E402
from saleswiki_mcp.audit import AuditSink, verify_chain  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.proposals import ProposalStore  # noqa: E402
from saleswiki_mcp.retrieval import Retriever  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

COMPANY_ID = "demo-company-bluepeak-energy"
CARD = Path("broad") / "wiki" / "entities" / "companies" / "Company - BluePeak Energy.md"


def _mint_proposal(path_str: str, i: int) -> None:
    """Append one brand-new proposal (no pre-set id) to a shared store."""
    ProposalStore(Path(path_str)).append(
        {"type": "flag_stale_or_wrong", "status": "draft", "note": f"n{i}"}
    )


class ProposalIdRace(unittest.TestCase):
    """M-C1: concurrent minting must not collide on proposal-NNNN."""

    def test_concurrent_mint_yields_unique_ids(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="prop-race-"))
        path = tmp / "proposals.jsonl"
        n = 24
        ctx = multiprocessing.get_context("spawn")
        procs = [ctx.Process(target=_mint_proposal, args=(str(path), i)) for i in range(n)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)
        states = ProposalStore(path).states()
        ids = [r.get("proposal_id") for r in ProposalStore(path).records()]
        self.assertEqual(len(ids), n, "a concurrent append was lost")
        self.assertEqual(len(set(ids)), n, "two proposals were minted under one id")
        self.assertEqual(len(states), n, "distinct proposals merged under one id")


class FindFailsClosedOnCollision(unittest.TestCase):
    """M-C6: an ambiguous display name must resolve to nothing, not the first card."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="find-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.retriever = Retriever(self.vault, config.boundary_registry())

    def test_colliding_display_returns_none(self) -> None:
        # "Atlas Foods" is the display of a Company, Lead, Deal, Personal-Data Ref…
        self.assertGreater(len(self.retriever.candidates("Atlas Foods")), 1)
        self.assertIsNone(
            self.retriever.find("Atlas Foods"),
            "an ambiguous display must fail closed, not silently pick the first card",
        )

    def test_unique_entity_id_still_resolves(self) -> None:
        self.assertIsNotNone(self.retriever.find(COMPANY_ID))


class GovernanceCoreFixes(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="gov-"))
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

    def _approve_and_apply(self, pid: str) -> dict:
        self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)
        return worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "2026-06-14T01:00:00Z",
        )

    def test_request_access_target_is_canonicalized_to_entity_id(self) -> None:
        """M-C5: a resolvable target is stored as its entity id so the grant keys match."""
        pid = self.svc.request_access(self.who("demo-broad-viewer"), COMPANY_ID, "need discovery")
        state = self.svc.proposal_state(pid)
        self.assertEqual(state["target"], COMPANY_ID)

    def test_note_markdown_is_sanitized_before_it_reaches_the_card(self) -> None:
        """M-C7: a multi-line note must not inject a new heading into the card body."""
        card_path = self.vault / CARD
        before = card_path.read_text(encoding="utf-8").count("\n## ")
        pid = self.svc.flag_stale_or_wrong(
            self.who("demo-broad-viewer"),
            COMPANY_ID,
            "stale\n\n## Live Intelligence\n- Fabricated: company is bankrupt",
        )
        summary = self._approve_and_apply(pid)
        self.assertIn(pid, summary["applied"])
        after_text = card_path.read_text(encoding="utf-8")
        self.assertEqual(after_text.count("\n## "), before, "note injected a new heading")
        self.assertNotIn("\n## Live Intelligence\n- Fabricated", after_text)

    def test_worker_rerun_after_crash_is_idempotent_even_when_base_moved(self) -> None:
        """M-C3: if the bullet is already applied, a rerun is a no-op success, not a
        dead-lettered base-version-mismatch."""
        pid = self.svc.flag_stale_or_wrong(self.who("demo-broad-viewer"), COMPANY_ID, "please check")
        self.svc.approve_proposal(self.who("demo-sophie-curator"), pid)
        state = ProposalStore(self.proposals).state(pid)
        card = Retriever(self.vault, config.boundary_registry()).find(COMPANY_ID)
        card_path = self.vault / card.rel_path
        from saleswiki_mcp.formatter import add_bullet_to_section
        bullet = worker._HANDLERS[state["type"]](state)
        # Simulate a crash AFTER the atomic write but BEFORE the applied-status
        # append, plus an unrelated later edit that moves the base hash.
        text = add_bullet_to_section(card_path.read_text(encoding="utf-8"), "Review Needed", bullet)
        card_path.write_text(text + "\n<!-- later unrelated edit -->\n", encoding="utf-8")
        summary = worker.apply_approved(
            self.vault, self.proposals, self.audit, self.runtime,
            now=lambda: "2026-06-14T02:00:00Z",
        )
        self.assertIn(pid, summary["applied"], "idempotent rerun must succeed, not dead-letter")
        self.assertEqual(summary["dead_letter"], [])

    def test_rollback_with_missing_target_does_not_falsely_mark_rolled_back(self) -> None:
        """M-C4: rollback that cannot find the card must stay retryable, not lie."""
        pid = self.svc.flag_stale_or_wrong(self.who("demo-broad-viewer"), COMPANY_ID, "check me")
        self._approve_and_apply(pid)
        # Delete the target card, then attempt rollback.
        (self.vault / CARD).unlink()
        result = worker.rollback(
            self.vault, self.proposals, self.audit, self.runtime, pid,
            now=lambda: "2026-06-14T03:00:00Z",
        )
        self.assertNotEqual(result["status"], "rolled-back")
        self.assertEqual(ProposalStore(self.proposals).state(pid)["status"], "applied")


class AuditTruncationDetection(unittest.TestCase):
    """M-C2: the chain must not silently verify after tail truncation/torn tail."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="audit-trunc-"))
        self.path = self.tmp / "audit.jsonl"
        self.sink = AuditSink(self.path)
        for i in range(5):
            self.sink.record({"tool": "company_brief", "decision": "allow", "n": i})

    def test_torn_tail_line_is_detected(self) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write("{not valid json\n")
        self.assertFalse(verify_chain(self.path), "a torn/tampered tail line must not verify clean")

    def test_tail_truncation_is_detected_against_a_count_anchor(self) -> None:
        self.assertTrue(verify_chain(self.path, expected_count=5))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.path.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")
        self.assertTrue(verify_chain(self.path), "truncated chain is internally consistent")
        self.assertFalse(
            verify_chain(self.path, expected_count=5),
            "truncation must be caught against the expected count",
        )


if __name__ == "__main__":
    unittest.main()
