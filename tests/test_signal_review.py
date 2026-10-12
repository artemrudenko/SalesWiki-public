"""Quality-check lifecycle, provenance, isolation and append-only concurrency."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

from scripts import generate_demo_vault as gdv
from saleswiki_mcp import config
from saleswiki_mcp.identity import FixtureIdentityProvider
from saleswiki_mcp.server import build_tools
from saleswiki_mcp.service import build_default_service

TARGET = "demo-company-atlas-foods"


def actor(name="demo-ethan-ae"):
    return FixtureIdentityProvider(name, config.identity_config()).resolve()


def request(**changes):
    return {"target": TARGET, "action": "start", "expected_revision": 0,
            "outcome": "", "cause": "unknown", "cause_status": "unknown", "decision_impact": "not_assessed",
            "next_action": "verify_source", "follow_up_on": "2026-10-20", "evidence_ids": [], **changes}


class SignalReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.vault = self.root / "vault"
        gdv.generate_permissioned_demo(self.vault)
        self.ledger = self.root / "runtime" / "signal-reviews.jsonl"
        self.service = build_default_service(self.vault, self.root / "audit.jsonl", self.root / "runtime" / "proposals.jsonl", now=lambda: "2026-10-12T09:00:00Z")
        self.before = {p: p.read_bytes() for p in self.vault.rglob("*.md")}
        initial = self.service.signal_review(actor(), TARGET)
        self.source = initial["sources"][0]["id"]
        self.initial_freshness = initial["card_freshness"]

    def test_start_complete_and_repeat_do_not_refresh_or_mutate_cards(self):
        self.assertEqual(self.service.record_signal_review(actor(), request())["state"], "in_progress")
        result = self.service.record_signal_review(actor(), request(action="complete", expected_revision=1,
                    outcome="update_needed", decision_impact="changed", next_action="propose_update", evidence_ids=[self.source]))
        self.assertEqual(result["state"], "completed")
        view = self.service.signal_review(actor(), TARGET)
        self.assertEqual(view["card_freshness"], self.initial_freshness)
        self.assertEqual(len(view["events"]), 2)
        self.assertEqual(view["events"][-1]["evidence_dates"][self.source], self.service._retriever.find(self.source).updated)
        self.assertNotIn("actor_id", view["events"][0])
        self.assertEqual(self.service.record_signal_review(actor(), request(expected_revision=2))["revision"], 3)
        for path, original in self.before.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.root / "runtime" / "proposals.jsonl").exists())

    def test_six_review_scenarios_keep_cause_separate_from_decision(self):
        scenarios = [
            ("confirmed_current", "unknown", "unknown", "unchanged", "none", [self.source]),
            ("update_needed", "source_changed", "suspected", "changed", "propose_update", [self.source]),
            ("unable_to_verify", "unknown", "unknown", "cannot_assess", "request_context", []),
            ("false_alarm", "false_alert", "confirmed", "unchanged", "none", [self.source]),
            ("unable_to_verify", "conflicting_sources", "suspected", "cannot_assess", "reconcile_summary", [self.source]),
            ("no_longer_relevant", "wrong_cadence", "suspected", "changed", "revisit_later", [self.source]),
        ]
        revision = 0
        for outcome, cause, status, impact, next_action, refs in scenarios:
            with self.subTest(outcome=outcome, cause=cause):
                self.service.record_signal_review(actor(), request(expected_revision=revision))
                result = self.service.record_signal_review(actor(), request(action="complete", expected_revision=revision + 1,
                    outcome=outcome, cause=cause, cause_status=status, decision_impact=impact, next_action=next_action,
                    follow_up_on="" if next_action == "none" else "2026-10-20", evidence_ids=refs))
                self.assertEqual(result["status"], "recorded")
                revision += 2
        self.assertEqual(self.service.signal_review(actor(), TARGET)["revision"], 12)

    def test_later_source_update_does_not_rewrite_recorded_source_date(self):
        self.service.record_signal_review(actor(), request())
        self.service.record_signal_review(actor(), request(action="complete", expected_revision=1,
                    outcome="confirmed_current", decision_impact="unchanged", next_action="none", follow_up_on="", evidence_ids=[self.source]))
        card = self.service._retriever.find(self.source)
        original_date = card.updated
        path = self.vault / card.rel_path
        path.write_text(path.read_text().replace(f"updated: {original_date}", "updated: 2026-10-13", 1))
        view = self.service.signal_review(actor(), TARGET)
        self.assertEqual(view["events"][-1]["evidence_dates"][self.source], original_date)
        self.assertEqual(next(source for source in view["sources"] if source["id"] == self.source)["date"], "2026-10-13")

    def test_people_cannot_see_each_others_checks_even_with_the_same_role(self):
        self.service.record_signal_review(actor(), request())
        for person in ("demo-olivia-marketing", "demo-sophie-curator", "demo-raj-revops"):
            view = self.service.signal_review(actor(person), TARGET)
            self.assertEqual(view["events"], [])
            self.assertEqual(view["state"], "not_started")

    def test_hidden_target_and_missing_target_have_the_same_shape(self):
        for target in ("missing", "demo-deal-bluepeak-energy-pilot"):
            self.assertEqual(self.service.signal_review(actor("demo-olivia-marketing"), target), {"status": "unavailable", "access": "blocked"})
        self.assertEqual(self.service.signal_review(actor("demo-broad-viewer"), TARGET)["status"], "unavailable")

    def test_unrelated_or_hidden_sources_cannot_be_recorded_or_disclosed(self):
        self.service.record_signal_review(actor("demo-olivia-marketing"), request())
        value = request(action="complete", expected_revision=1, outcome="update_needed", decision_impact="changed", evidence_ids=["demo-deal-bluepeak-energy-pilot"])
        self.assertEqual(self.service.record_signal_review(actor("demo-olivia-marketing"), value)["status"], "unavailable")
        self.assertEqual(len(self.ledger.read_text().splitlines()), 1)
        # Move a previously cited source into a denied boundary: current access
        # is re-evaluated, even though the check was allowed when recorded.
        self.service.record_signal_review(actor(), request())
        self.service.record_signal_review(actor(), {**value, "evidence_ids": [self.source]})
        card = self.service._retriever.find(self.source)
        path = self.vault / card.rel_path
        moved = self.vault / "personal-data" / "sources" / path.name
        moved.parent.mkdir(parents=True, exist_ok=True)
        path.rename(moved)
        self.assertEqual(self.service.signal_review(actor(), TARGET), {"status": "unavailable", "access": "blocked"})

    def test_duplicate_and_concurrent_save_are_conflicts(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: self.service.record_signal_review(actor(), request()), range(2)))
        self.assertEqual(sorted(item["status"] for item in outcomes), ["conflict", "recorded"])
        self.assertEqual(len(self.ledger.read_text().splitlines()), 1)

    def test_invalid_content_or_claims_do_not_enter_the_journal(self):
        invalid = [{"role": "admin"}, {"cause": "sync_failed", "cause_status": "confirmed"}, {"follow_up_on": "2026-02-30"},
                   {"follow_up_on": "2026-10-01"}, {"expected_revision": True}, {"outcome": "customer secret"}, {"action": []}]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.service.record_signal_review(actor(), request(**changes))
        self.assertFalse(self.ledger.exists())

    def test_corrupt_history_fails_without_reporting_a_successful_check(self):
        self.ledger.parent.mkdir(exist_ok=True)
        for content in ('{torn', '["unexpected"]', json.dumps({"target": TARGET})):
            self.ledger.write_text(content + "\n")
            self.assertEqual(self.service.signal_review(actor(), TARGET)["status"], "error")
            self.assertEqual(self.service.record_signal_review(actor(), request())["status"], "error")
            self.assertEqual(self.ledger.read_text(), content + "\n")

    def test_mcp_handlers_share_the_same_permissioned_lifecycle(self):
        tools = build_tools(self.service, actor())
        self.assertEqual(tools["saleswiki.signal_review"](TARGET)["state"], "not_started")
        self.assertEqual(tools["saleswiki.record_signal_review"](**request())["status"], "recorded")


if __name__ == "__main__":
    unittest.main()
