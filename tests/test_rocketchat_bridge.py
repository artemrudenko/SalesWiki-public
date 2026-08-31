"""Regression tests for the Rocket.Chat bridge's intent routing and role aliases.

The bridge advertises a fixed set of `?`-questions in its `демо` cheat-sheet;
these tests guard that every advertised phrasing actually routes to the right
read tool (a stem mismatch once made `подготовка к звонку` silently fail).
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations" / "rocketchat"))

import bridge  # noqa: E402
from saleswiki_mcp import config, server  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402


_ENV_PATCHER: mock._patch_dict | None = None


def setUpModule() -> None:
    """Keep bridge tests deterministic even when the developer shell has live
    Rocket.Chat / LLM demo variables exported."""
    global _ENV_PATCHER
    _ENV_PATCHER = mock.patch.dict(
        bridge.os.environ,
        {
            "RC_LLM_SUMMARY": "0",
            "RC_LLM_RECS": "0",
            "ANTHROPIC_API_KEY": "",
        },
    )
    _ENV_PATCHER.start()


def tearDownModule() -> None:
    if _ENV_PATCHER is not None:
        _ENV_PATCHER.stop()


class IntentRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _method(self, question: str) -> str | None:
        intent = self.wiki._match_intent(question)
        return intent[0] if intent else None

    def test_call_prep_phrasings_all_route(self) -> None:
        for q in (
            "подготовка к звонку BluePeak Energy",
            "звонок BluePeak Energy",
            "call prep BluePeak Energy",
        ):
            self.assertEqual(self._method(q), "call_prep", f"should route: {q!r}")

    def test_core_intents_route(self) -> None:
        cases = {
            "бриф по BluePeak Energy": "company_brief",
            "риск по сделке BluePeak Energy": "deal_risk",
            "приоритет лида BluePeak Energy": "lead_priority",
            "пайплайн": "pipeline_risk_digest",
            "мой день": "my_day",
            "контент-идеи": "content_opportunities",
            "кампания Q3 ROI Push": "campaign_brief",
            "бриф по событию Sales Tech Summit 2026": "event_brief",
        }
        for q, method in cases.items():
            self.assertEqual(self._method(q), method, f"should route: {q!r}")

    def test_bare_lead_priority_shows_all_not_a_default_company(self) -> None:
        # No company named -> all leads (full funnel), not a surprise BluePeak default.
        self.assertIsNone(self.wiki._match_intent("приоритет лида")[2])
        self.assertEqual(self.wiki._match_intent("приоритет лида BluePeak Energy")[2], "BluePeak Energy")

    def test_prospect_companies_are_recognized(self) -> None:
        for name in ("Vertex Logistics", "Lumen Retail", "Orchard Bank"):
            self.assertEqual(self.wiki._match_intent(f"бриф по {name}")[2], name)

    def test_cross_company_deal_risk_drops_company(self) -> None:
        intent = self.wiki._match_intent("риск по всем сделкам")
        self.assertEqual(intent[0], "deal_risk")
        self.assertIsNone(intent[2], "'все' must mean cross-company (company=None)")

    def test_role_aliases_resolve(self) -> None:
        self.assertEqual(bridge.resolve_role("ae"), "account-exec")
        self.assertEqual(bridge.resolve_role("HoS"), "head-of-sales")
        self.assertEqual(bridge.resolve_role("viewer"), "employee")
        self.assertIsNone(bridge.resolve_role("nonsense"))


class PolicyDrift(unittest.TestCase):
    """FINDING 3: the bridge must derive its role→boundary gating from the
    canonical policy (schemas/access-policy.json), never a hardcoded shadow copy
    that can silently drift from what the gateway actually enforces."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.policy_roles = {r["id"]: set(r.get("boundaries", []))
                            for r in config.access_policy()["roles"]}
        cls.actor_role = {u["id"]: u["role"]
                          for u in config.identity_config()["providers"]["fixture"]["users"]}

    def test_bridge_boundaries_equal_canonical_policy_for_every_role(self) -> None:
        covered: set[str] = set()
        for chat_role, (actor_id, _desc) in bridge.ROLES.items():
            policy_role = self.actor_role[actor_id]
            covered.add(policy_role)
            self.assertEqual(
                bridge.ROLE_BOUNDARIES[chat_role], self.policy_roles[policy_role],
                f"bridge boundary set for `{chat_role}` drifted from policy role `{policy_role}`",
            )
        self.assertEqual(covered, set(self.policy_roles),
                         "every role in the policy JSON must be reachable from a chat role")

    def test_unlock_hints_only_name_roles_that_hold_the_boundary(self) -> None:
        for boundary, roles in bridge.BOUNDARY_UNLOCK_ROLES.items():
            self.assertTrue(roles, f"no unlock roles derived for {boundary}")
            for role in roles:
                self.assertIn(boundary, bridge.ROLE_BOUNDARIES[role],
                              f"unlock hint names `{role}` which does not hold `{boundary}` in policy")

    def test_audience_legend_matches_boundary_holders(self) -> None:
        for boundary in ("sales-confidential", "personal-data"):
            holders = [r for r in bridge.ROLES if boundary in bridge.ROLE_BOUNDARIES[r]]
            for role in holders:
                self.assertIn(role, bridge.BOUNDARY_AUDIENCE[boundary],
                              f"audience legend for `{boundary}` must name holder `{role}`")


class GovernanceProposals(unittest.TestCase):
    """The bridge wraps all three propose tools: access, flag-stale, redaction."""

    def setUp(self) -> None:
        self.wiki = bridge.Wiki()
        self.state = {
            "role": "employee", "trigger": "?",
            "company_name": "BluePeak Energy", "company_id": "demo-company-bluepeak-energy",
        }

    def _curator(self) -> dict:
        return {**self.state, "role": "curator"}

    def test_flag_stale_creates_reviewable_proposal(self) -> None:
        out = bridge.handle("пометить устаревшим цена больше не актуальна", wiki=self.wiki, state=self.state)
        self.assertRegex(out, r"proposal-\d+")
        queue = bridge.handle("очередь ревью", wiki=self.wiki, state=self._curator())
        self.assertIn("proposal-", queue)

    def test_request_redaction_creates_proposal(self) -> None:
        out = bridge.handle("запросить редактуру скрыть имена контактов", wiki=self.wiki, state=self.state)
        self.assertRegex(out, r"proposal-\d+")

    def test_redaction_not_routed_as_access_request(self) -> None:
        out = bridge.handle("запросить редактуру причина", wiki=self.wiki, state=self.state)
        self.assertNotIn("Access request created", out, "redaction must not be treated as an access request")

    def test_flag_default_note_when_empty(self) -> None:
        out = bridge.handle("пометить устаревшим", wiki=self.wiki, state=self.state)
        self.assertRegex(out, r"proposal-\d+")

    def test_approving_flag_does_not_claim_data_access(self) -> None:
        bridge.handle("пометить устаревшим устарело", wiki=self.wiki, state=self.state)
        msg = bridge.handle("одобрить 1", wiki=self.wiki, state=self._curator())
        self.assertIn("Review Needed", msg)
        self.assertNotIn("Access granted", msg)

    def test_approving_access_request_grants_data(self) -> None:
        bridge.handle("запросить доступ нужен риск", wiki=self.wiki, state=self.state)
        msg = bridge.handle("одобрить 1", wiki=self.wiki, state=self._curator())
        self.assertIn("Access granted", msg)

    def test_apply_runs_worker_and_writes_review_needed(self) -> None:
        bridge.handle("пометить устаревшим цена устарела", wiki=self.wiki, state=self.state)
        bridge.handle("одобрить 1", wiki=self.wiki, state=self._curator())
        msg = bridge.handle("применить", wiki=self.wiki, state=self._curator())
        self.assertIn("Review Needed", msg)
        self.assertRegex(msg, r"proposal-\d+")
        # The single-writer worker advanced the proposal to 'applied'.
        self.assertEqual(self.wiki.svc.proposal_state("proposal-0001").get("status"), "applied")

    def test_apply_with_nothing_approved_says_so(self) -> None:
        # Reviewer runs apply but nothing is approved: a clear info message, not a crash.
        out = bridge.handle("применить", wiki=self.wiki, state=self._curator())
        self.assertIn("No approved requests to apply", out)

    def test_apply_reports_worker_spawn_failure(self) -> None:
        bridge.handle("пометить устаревшим цена устарела", wiki=self.wiki, state=self.state)
        bridge.handle("одобрить 1", wiki=self.wiki, state=self._curator())
        with mock.patch("bridge.subprocess.run", side_effect=OSError("no python")):
            out = bridge.handle("применить", wiki=self.wiki, state=self._curator())
        self.assertIn("Could not start the worker", out)

    def test_apply_blocked_for_non_reviewer(self) -> None:
        out = bridge.handle("применить", wiki=self.wiki, state=self.state)  # employee
        self.assertIn("🔒", out)


class UnknownCompanyHonesty(unittest.TestCase):
    """An explicit company name that matches no catalog entry must yield the
    honest not-found reply — `? бриф по Acme Industrial` (the demo's scripted
    not-found beat) used to silently become BluePeak Energy (catalog[0])."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str = "employee") -> dict:
        return {"role": role, "trigger": "?", "company_name": "BluePeak Energy",
                "company_id": "demo-company-bluepeak-energy"}

    def test_unknown_company_brief_is_honest_not_found(self) -> None:
        out = bridge.handle("? бриф по Acme Industrial", wiki=self.wiki, state=self._state())
        self.assertNotIn("BluePeak", out, "unknown company must not default to catalog[0]")
        self.assertIn("ℹ️", out)

    def test_scripted_tesla_beat_is_not_found(self) -> None:
        # Advertised in the demo cheat-sheet: "? company brief Tesla" -> honest not-found.
        out = bridge.handle("? company brief Tesla", wiki=self.wiki, state=self._state())
        self.assertNotIn("BluePeak", out)
        self.assertIn("ℹ️", out)

    def test_unknown_company_call_prep_is_not_found(self) -> None:
        out = bridge.handle("? call prep Acme Industrial", wiki=self.wiki, state=self._state("account-exec"))
        self.assertNotIn("BluePeak", out)

    def test_unknown_intent_arg_routes_raw_name(self) -> None:
        # The unmatched raw name flows to the service so its Answer-envelope
        # not-found is what the user sees.
        intent = self.wiki._match_intent("бриф по Acme Industrial")
        self.assertEqual(intent[0], "company_brief")
        self.assertEqual(intent[2], "Acme Industrial")

    def test_known_company_still_matches(self) -> None:
        out = bridge.handle("? бриф по BluePeak Energy", wiki=self.wiki, state=self._state())
        self.assertIn("BluePeak Energy", out)
        self.assertNotIn("ℹ️ Cannot answer", out)

    def test_partial_company_name_resolves_to_catalog_entry(self) -> None:
        # A unique partial ("Atlas") must resolve to the real card, not not-found
        # and not a silent BluePeak default.
        self.assertEqual(self.wiki._match_intent("бриф по Atlas")[2], "Atlas Foods")
        self.assertEqual(self.wiki._match_intent("бриф BluePeak")[2], "BluePeak Energy")

    def test_bare_brief_keeps_demo_default(self) -> None:
        # No company mentioned at all -> the demo default still shows something.
        self.assertEqual(self.wiki._match_intent("дай бриф")[2], "BluePeak Energy")

    def test_bare_no_arg_questions_keep_working(self) -> None:
        for q in ("? мой день", "? пайплайн"):
            out = bridge.handle(q, wiki=self.wiki, state=self._state("head-of-sales"))
            self.assertNotIn("Cannot answer", out, f"bare question must keep working: {q!r}")


class McpModeGovernance(unittest.TestCase):
    """RC_USE_MCP mode: the bridge must pass the approver's TTL through the MCP
    tool and must read decision semantics from the server's structured envelope
    — never by keyword-sniffing the rendered text — so a server wording change
    can never flip a no-op into a fresh grant. Envelopes are produced by the
    REAL server tool handlers (server.build_tools over the
    same service), so the contract is exercised against actual server output
    without needing the mcp SDK."""

    def setUp(self) -> None:
        self.wiki = bridge.Wiki()
        self.state = {
            "role": "employee", "trigger": "?",
            "company_name": "BluePeak Energy", "company_id": "demo-company-bluepeak-energy",
        }
        bridge.handle("запросить доступ нужен риск", wiki=self.wiki, state=self.state)
        self.pid = "proposal-0001"
        curator = FixtureIdentityProvider("demo-marina-curator", config.identity_config()).resolve()
        self.server_tools = server.build_tools(self.wiki.svc, curator)

    def _stub_mcp(self, envelope: dict) -> list:
        """Replace the per-request MCP spawn with a canned server envelope,
        mirroring _mcp_call's (text, structured) contract; returns the recorded
        (tool, kwargs) calls."""
        calls: list = []

        async def fake(actor_id: str, tool: str, kwargs: dict) -> tuple[str, dict]:
            calls.append((tool, kwargs))
            return envelope.get("text", ""), {k: v for k, v in envelope.items() if k != "text"}

        self.wiki.use_mcp = True
        self.wiki._mcp_call = fake
        return calls

    def test_approve_passes_ttl_days_over_mcp(self) -> None:
        # `одобрить <id> 7` must send ttl_days=7 to the MCP tool, not drop it.
        calls = self._stub_mcp({"text": f"Proposal {self.pid} approved.",
                                "status": "approved", "proposal_id": self.pid})
        out = self.wiki.decide("curator", "approve", self.pid, ttl_days=7)
        tool, kwargs = calls[0]
        self.assertEqual(tool, "saleswiki.approve_proposal")
        self.assertEqual(kwargs.get("ttl_days"), 7)
        self.assertIn("7 days", out, "the confirmation must reflect the approver's TTL")

    def test_first_approve_over_mcp_reports_grant(self) -> None:
        self._stub_mcp(self.server_tools["saleswiki.approve_proposal"](self.pid))
        out = self.wiki.decide("curator", "approve", self.pid)
        self.assertIn("Access granted", out)

    def test_reapprove_over_mcp_does_not_claim_a_new_grant(self) -> None:
        self.server_tools["saleswiki.approve_proposal"](self.pid)
        noop_envelope = self.server_tools["saleswiki.approve_proposal"](self.pid)
        self._stub_mcp(noop_envelope)
        out = self.wiki.decide("curator", "approve", self.pid)
        self.assertNotIn("Access granted", out, "a no-op re-approve must not read as a fresh grant")
        self.assertIn("already", out.lower())

    def test_wording_drift_cannot_flip_semantics_over_mcp(self) -> None:
        # Fully reworded prose with a correct envelope must still classify as a
        # no-op — semantics come from the envelope alone.
        self._stub_mcp({"text": "Acknowledged. This decision was recorded some time ago.",
                        "status": "approved", "reason": "not in draft", "proposal_id": self.pid})
        out = self.wiki.decide("curator", "approve", self.pid)
        self.assertNotIn("Access granted", out)
        self.assertIn("already", out.lower())

    def test_revoke_noop_is_honest_over_mcp(self) -> None:
        self._stub_mcp({"text": "Nothing to revoke here.", "status": "rejected",
                        "reason": "not an active grant", "proposal_id": self.pid})
        out = self.wiki.decide("curator", "revoke", self.pid, reason="cleanup")
        self.assertNotIn("without access again", out, "a no-op revoke must not read as a fresh revoke")
        self.assertIn("already", out.lower())

    def test_reapprove_in_process_does_not_claim_a_new_grant(self) -> None:
        curator_state = {**self.state, "role": "curator"}
        first = bridge.handle("одобрить 1", wiki=self.wiki, state=curator_state)
        self.assertIn("Access granted", first)
        second = bridge.handle("одобрить 1", wiki=self.wiki, state=curator_state)
        self.assertNotIn("Access granted", second)
        self.assertIn("already", second.lower())

    def test_revoke_noop_in_process_is_honest(self) -> None:
        # Revoking an already-revoked grant must say so, not claim a fresh revoke
        # (the same envelope-driven no-op path as over MCP).
        self.wiki.decide("curator", "approve", self.pid)
        first = self.wiki.decide("curator", "revoke", self.pid, reason="cleanup")
        self.assertIn("revoked", first.lower())
        second = self.wiki.decide("curator", "revoke", self.pid, reason="cleanup")
        self.assertNotIn("without access again", second, "a no-op revoke must not read as a fresh revoke")
        self.assertIn("already", second.lower())


class DemoCommand(unittest.TestCase):
    def _h(self, text: str):
        return bridge.handle(text, wiki=None, state={"role": "employee", "trigger": "?"})

    def test_bare_demo_returns_full_catalogue(self) -> None:
        out = self._h("демо")
        self.assertIn("full catalogue of scenarios", out.lower())
        self.assertIn("demo marketing", out)  # role picker present

    def test_demo_role_russian_alias(self) -> None:
        out = self._h("демо маркетинг")
        self.assertIn("role `marketing`", out)
        self.assertIn("? campaign", out)
        self.assertIn("no-leak", out)

    def test_demo_role_english_and_short_alias(self) -> None:
        self.assertIn("role `account-exec`", self._h("демо account-exec"))
        self.assertIn("role `account-exec`", self._h("демо ae"))

    def test_demo_unknown_role(self) -> None:
        out = self._h("демо ерунда")
        self.assertIn("I don't know role", out)

    def test_demo_role_shows_blocked_section(self) -> None:
        out = self._h("демо employee")
        self.assertIn("What they CANNOT do", out)
        self.assertIn("🔒", out)


class LifecycleHelp(unittest.TestCase):
    """`как это работает` teaches the four mechanics: birth, immutability,
    the governance write-loop and state transitions (funnel/freshness)."""

    def _h(self, text: str):
        return bridge.handle(text, wiki=None, state={"role": "employee", "trigger": "?"})

    def test_lifecycle_covers_four_mechanics(self) -> None:
        out = self._h("как это работает")
        # 1. birth via the new_entity chokepoint + id ledger
        self.assertIn("new_entity", out)
        self.assertIn("ledger", out.lower())
        # 2. immutability of the controlled core
        self.assertIn("profile_lock", out)
        self.assertIn("Controlled Profile", out)
        # 3. governance write-loop
        self.assertIn("Review Needed", out)
        self.assertIn("apply", out)
        # 4. state transitions: funnel + freshness
        self.assertIn("MQL", out)
        self.assertIn("stale", out.lower())

    def test_lifecycle_aliases_route(self) -> None:
        for cmd in ("жизненный цикл", "lifecycle", "как работает система"):
            self.assertIn("Review Needed", self._h(cmd), f"alias should route: {cmd!r}")


class CardXray(unittest.TestCase):
    """`карточка <компания>` is the presenter reveal: the full source-of-truth
    across all access zones, with the card's governance sections annotated."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, **kw) -> dict:
        s = {"role": "curator", "trigger": "?", "company_name": "Atlas Foods",
             "company_id": "demo-company-atlas-foods"}
        s.update(kw)
        return s

    def test_xray_shows_full_card_zones(self) -> None:
        out = bridge.handle("карточка Atlas Foods", wiki=self.wiki, state=self._state())
        self.assertIn("Atlas Foods", out)
        self.assertIn("Controlled Profile", out)
        self.assertIn("Review Needed", out)
        self.assertIn("Change History", out)
        self.assertIn("profile_lock", out)  # governance frontmatter is explained

    def test_xray_reveals_closed_zone_files(self) -> None:
        out = bridge.handle("карточка Atlas Foods", wiki=self.wiki, state=self._state())
        self.assertIn("sales-confidential", out)
        self.assertIn("Deal - Atlas Foods", out)  # closed-zone card listed by name

    def test_xray_defaults_to_current_company(self) -> None:
        out = bridge.handle("карточка", wiki=self.wiki, state=self._state(company_name="Cedar Health"))
        self.assertIn("Cedar Health", out)

    def test_xray_hides_closed_zone_card_names_from_unauthorized_role(self) -> None:
        # An employee cannot read sales-confidential; the reveal must NOT leak the
        # closed-zone card stems (deal/person names are themselves the secret).
        out = bridge.handle("карточка Atlas Foods", wiki=self.wiki, state=self._state(role="employee"))
        self.assertNotIn("Deal - Atlas Foods", out, "closed-zone card name leaked to employee")

    def test_xray_still_teaches_that_a_closed_zone_exists(self) -> None:
        # Teaching value is preserved: the employee learns a closed zone exists,
        # how many cards, and which role unlocks it — without the names.
        out = bridge.handle("карточка Atlas Foods", wiki=self.wiki, state=self._state(role="employee"))
        self.assertIn("sales-confidential", out)
        low = out.lower()
        self.assertTrue("switch" in low or "role" in low, "should hint how to unlock the zone")

    def test_xray_hides_other_teams_closed_zone_from_constrained_role(self) -> None:
        # account-exec is ownership-constrained on sales-confidential (ABAC, not
        # just RBAC): viewing ANOTHER team's account must NOT list its closed-zone
        # stems, even though the AE's role nominally "sees" the boundary. Northstar
        # Robotics is owned by another team (sales-east); the gateway blocks its
        # deal_risk for this AE, so the reveal must match.
        out = bridge.handle(
            "карточка Northstar Robotics", wiki=self.wiki,
            state=self._state(role="account-exec", company_name="Northstar Robotics",
                              company_id="demo-company-northstar-robotics"),
        )
        self.assertNotIn("Deal - Northstar Robotics", out,
                         "another team's closed-zone deal leaked to a constrained AE")
        self.assertNotIn("MechRival", out,
                         "another team's competitor intel leaked to a constrained AE")

    def test_xray_reveals_own_account_closed_zone_to_constrained_role(self) -> None:
        # The same constrained AE viewing an account they OWN still sees the
        # closed-zone stems — the ABAC gate reveals exactly what the gateway would
        # let them read, so the demo's flagship reveal is preserved.
        out = bridge.handle(
            "карточка BluePeak Energy", wiki=self.wiki,
            state=self._state(role="account-exec", company_name="BluePeak Energy",
                              company_id="demo-company-bluepeak-energy"),
        )
        self.assertIn("Deal - BluePeak Energy", out,
                      "AE must still see closed-zone cards for an account they own")


class GoogleDriveIngest(unittest.TestCase):
    """The synthetic Google Drive connector: list a 'connected' folder, answer
    yes/no resources, and turn 'process' into an `ingest_resource` proposal that
    rides the same review → approve → apply loop. Folder visibility is no-leak."""

    def setUp(self) -> None:
        self.wiki = bridge.Wiki()

    def _state(self, role: str = "account-exec") -> dict:
        return {"role": role, "trigger": "?", "company_name": "Atlas Foods",
                "company_id": "demo-company-atlas-foods"}

    def test_drive_lists_folders_with_new_counts(self) -> None:
        out = bridge.handle("драйв", wiki=self.wiki, state=self._state())
        self.assertIn("Sales/Q3-Calls", out)
        self.assertIn("Marketing/Webinars", out)
        self.assertIn("new", out.lower())  # "N new" summary present

    def test_drive_folder_lists_resources_when_authorized(self) -> None:
        out = bridge.handle("драйв Sales/Q3-Calls", wiki=self.wiki, state=self._state("account-exec"))
        self.assertIn("gd-001", out)
        self.assertIn("Atlas Foods", out)
        self.assertIn("process", out.lower())

    def test_drive_folder_no_leak_for_unauthorized_role(self) -> None:
        # employee must NOT see the contents of a sales-confidential folder.
        out = bridge.handle("драйв Sales/Q3-Calls", wiki=self.wiki, state=self._state("employee"))
        self.assertIn("🔒", out)
        self.assertNotIn("gd-001", out)

    def test_marketing_sees_broad_folder(self) -> None:
        out = bridge.handle("драйв Marketing/Webinars", wiki=self.wiki, state=self._state("marketing"))
        self.assertIn("gd-010", out)

    def test_process_creates_ingest_proposal(self) -> None:
        out = bridge.handle("обработать gd-001", wiki=self.wiki, state=self._state("account-exec"))
        self.assertRegex(out, r"proposal-\d+")
        queue = bridge.handle("очередь ревью", wiki=self.wiki, state=self._state("curator"))
        self.assertIn("ingest_resource", queue)

    def test_approve_ingest_does_not_claim_access_grant(self) -> None:
        # Approving an ingest_resource queues a card update; it must never be
        # reported as a data-access grant (that wording is for request_access only).
        bridge.handle("обработать gd-001", wiki=self.wiki, state=self._state("account-exec"))
        msg = bridge.handle("одобрить 1", wiki=self.wiki, state=self._state("curator"))
        self.assertNotIn("Access granted", msg)
        self.assertIn("NOT grant data access", msg)

    def test_process_then_approve_apply_writes_review_needed(self) -> None:
        bridge.handle("обработать gd-001", wiki=self.wiki, state=self._state("account-exec"))
        bridge.handle("одобрить 1", wiki=self.wiki, state=self._state("curator"))
        msg = bridge.handle("применить", wiki=self.wiki, state=self._state("curator"))
        self.assertIn("Review Needed", msg)
        self.assertEqual(self.wiki.svc.proposal_state("proposal-0001").get("status"), "applied")

    def test_process_unknown_id_is_handled(self) -> None:
        out = bridge.handle("обработать gd-999", wiki=self.wiki, state=self._state("account-exec"))
        self.assertNotRegex(out, r"proposal-\d+")
        self.assertIn("gd-999", out)

    def test_process_all_creates_a_proposal_per_new_visible_file(self) -> None:
        out = bridge.handle("обработать всё", wiki=self.wiki, state=self._state("account-exec"))
        # AE sees Sales/Q3-Calls (2 new) + Marketing/Webinars (1 new) = 3 new files.
        import re as _re
        self.assertGreaterEqual(len(set(_re.findall(r"proposal-\d+", out))), 2)

    def test_process_blocked_file_in_unauthorized_folder(self) -> None:
        # employee cannot process a file that lives in a sales-confidential folder.
        out = bridge.handle("обработать gd-001", wiki=self.wiki, state=self._state("employee"))
        self.assertNotRegex(out, r"proposal-\d+")
        self.assertIn("🔒", out)


class ReviewFixes(unittest.TestCase):
    """Demo cross-review P1/P2: name the unlocking role in every 🔒, reframe the
    AE banner (commercial access already granted), friendly brief headings, and
    an honest no-leak pipeline for roles without deal access."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str) -> dict:
        return {"role": role, "trigger": "?", "company_name": "BluePeak Energy",
                "company_id": "demo-company-bluepeak-energy"}

    def test_blocked_message_names_required_role(self) -> None:
        out = bridge.handle("? риск по сделке BluePeak Energy", wiki=self.wiki, state=self._state("employee"))
        self.assertIn("🔒", out)
        self.assertIn("account-exec", out)
        self.assertIn("Needs role", out)

    def test_sanitized_brief_notice_names_role_for_employee(self) -> None:
        out = bridge.handle("? бриф по BluePeak Energy", wiki=self.wiki, state=self._state("employee"))
        self.assertIn("Needs role", out)
        self.assertIn("sales-confidential", out)

    def test_ae_brief_notice_is_by_request_not_scary(self) -> None:
        # AE has commercial access; only personal-data is withheld -> by-request note.
        out = bridge.handle("? бриф по BluePeak Energy", wiki=self.wiki, state=self._state("account-exec"))
        self.assertIn("personal-data", out)
        self.assertIn("You have commercial access", out)
        self.assertNotIn("Some data is hidden for role `account-exec`", out)

    def test_brief_headings_are_friendly_without_zone_prefix(self) -> None:
        out = bridge.handle("? бриф по BluePeak Energy", wiki=self.wiki, state=self._state("account-exec"))
        self.assertNotIn("Sales Confidential -", out)
        self.assertNotIn("Broad -", out)
        self.assertIn("(confidential)", out)

    def test_marketing_pipeline_is_explicit_no_leak(self) -> None:
        out = bridge.handle("? пайплайн", wiki=self.wiki, state=self._state("marketing"))
        self.assertIn("🔒", out)
        self.assertNotIn("$", out)  # no figures leak


class SecondPassFixes(unittest.TestCase):
    """Findings from the 2nd cross-review pass: a top-tier role gets no
    nonsensical 'switch to a wider role' hint; ABAC (ownership) masking is not
    mislabelled as 'only personal data'; the personal-data heading is friendly;
    my_day has no doubled section headers; the lead 'Linked deal' cell doesn't
    stutter."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str, company: str = "Atlas Foods") -> dict:
        return {"role": role, "trigger": "?", "company_name": company,
                "company_id": bridge.Wiki.company_id(company)}

    def test_curator_brief_no_nonsensical_higher_role_hint(self) -> None:
        out = bridge.handle("? бриф по Atlas Foods", wiki=self.wiki, state=self._state("curator"))
        self.assertNotIn("a role with broader access", out)

    def test_personal_data_heading_is_friendly(self) -> None:
        out = bridge.handle("? бриф по Atlas Foods", wiki=self.wiki, state=self._state("admin"))
        # The section heading is friendly; the raw card name may still appear in
        # the Sources/provenance line, which is fine.
        self.assertIn("## Personal data", out)
        self.assertNotIn("## Personal Data Ref", out)

    def test_myday_has_no_doubled_section_headers(self) -> None:
        out = bridge.handle("? мой день", wiki=self.wiki, state=self._state("account-exec"))
        self.assertNotIn("## Deals At Risk", out)  # embedded deal header dropped
        self.assertIn("Leads To Act On", out)

    def test_lead_cell_does_not_stutter(self) -> None:
        out = bridge.handle("? мой день", wiki=self.wiki, state=self._state("account-exec"))
        self.assertNotIn("Linked deal: Linked deal risk:", out)

    def test_myday_ae_does_not_mislabel_ownership_masking(self) -> None:
        out = bridge.handle("? мой день", wiki=self.wiki, state=self._state("account-exec"))
        if "🔒" in out:  # a deal is masked by ownership
            self.assertNotIn("Only personal data", out)

    def test_sources_are_deduped_and_one_per_line(self) -> None:
        out = bridge.handle("? мой день", wiki=self.wiki, state=self._state("account-exec"))
        self.assertIn("📎 Sources", out)
        # my_day used to list each deal twice (lead-linked + deal_risk) — dedup it.
        self.assertEqual(out.count("Deal — BluePeak Energy — Pilot"), 1)
        # one source per line: a bulletised list, not a single " · "-joined line.
        self.assertIn("\n   - ", out)

    def test_footer_has_blank_line_before_sources(self) -> None:
        out = bridge.handle("? пайплайн", wiki=self.wiki, state=self._state("head-of-sales"))
        self.assertIn("\n\n📎 Sources", out)


class ModelSummary(unittest.TestCase):
    """A '🤖 Сводка' headline composed strictly from the cited envelope (the LLM
    client rephrases cited facts, never invents). Deterministic offline by
    default; a real LLM is opt-in behind RC_LLM_SUMMARY."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str, co: str = "BluePeak Energy") -> dict:
        return {"role": role, "trigger": "?", "company_name": co,
                "company_id": bridge.Wiki.company_id(co)}

    def test_digest_has_grounded_summary_on_top(self) -> None:
        out = bridge.handle("? пайплайн", wiki=self.wiki, state=self._state("head-of-sales"))
        self.assertIn("🤖 Summary", out)
        head = out.split("\n## ", 1)[0]  # the part above the first section
        self.assertIn("🤖 Summary", head)
        self.assertIn("$420k", head)  # grounded: surfaces the top cited value

    def test_brief_has_summary(self) -> None:
        out = bridge.handle("? бриф по BluePeak Energy", wiki=self.wiki, state=self._state("account-exec"))
        self.assertIn("🤖 Summary", out)

    def test_blocked_answer_has_no_summary(self) -> None:
        out = bridge.handle("? риск по сделке BluePeak Energy", wiki=self.wiki, state=self._state("employee"))
        self.assertNotIn("🤖 Summary", out)

    def test_summary_is_deterministic_offline_by_default(self) -> None:
        a = bridge.handle("? мой день", wiki=self.wiki, state=self._state("account-exec"))
        b = bridge.handle("? мой день", wiki=self.wiki, state=self._state("account-exec"))
        self.assertEqual(a, b)


class LlmRecommendations(unittest.TestCase):
    """Opt-in '🧠 Recommendations' block: an LLM ranks and prioritizes a digest
    strictly from the cited envelope. Off by default, digest-only (my_day /
    pipeline / all-deals risk), clearly labeled as generated, fail-silent —
    the deterministic answer must stand alone on any LLM failure."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str = "account-exec") -> dict:
        return {"role": role, "trigger": "?", "company_name": "BluePeak Energy",
                "company_id": "demo-company-bluepeak-energy"}

    def _enabled(self):
        return mock.patch.dict(bridge.os.environ,
                               {"RC_LLM_RECS": "1", "RC_LLM_SUMMARY": "0",
                                "ANTHROPIC_API_KEY": "test-key"})

    def test_off_by_default(self) -> None:
        out = bridge.handle("? мой день", wiki=self.wiki, state=self._state())
        self.assertNotIn(bridge.RECS_MARKER, out)

    def test_digest_gets_labeled_block_when_enabled(self) -> None:
        with self._enabled(), mock.patch.object(
                bridge.Wiki, "_llm_call", return_value="1. Call BluePeak Energy first — hot lead."):
            out = bridge.handle("? мой день", wiki=self.wiki, state=self._state())
        self.assertIn(bridge.RECS_MARKER, out)
        self.assertIn("Call BluePeak Energy first", out)

    def test_prompt_is_grounded_on_the_envelope_only(self) -> None:
        seen: dict = {}

        def capture(self, prompt: str, max_tokens: int) -> str:  # noqa: ANN001
            seen["prompt"] = prompt
            return "ranked list"

        with self._enabled(), mock.patch.object(bridge.Wiki, "_llm_call", capture):
            bridge.handle("? мой день", wiki=self.wiki, state=self._state())
        self.assertIn("ONLY", seen["prompt"])  # the no-new-facts instruction
        self.assertIn("My Day", seen["prompt"])  # the envelope text rides along

    def test_non_digest_answers_have_no_block(self) -> None:
        with self._enabled(), mock.patch.object(
                bridge.Wiki, "_llm_call", return_value="should not appear"):
            out = bridge.handle("? бриф по BluePeak Energy", wiki=self.wiki, state=self._state())
        self.assertNotIn(bridge.RECS_MARKER, out)

    def test_blocked_answer_has_no_block(self) -> None:
        with self._enabled(), mock.patch.object(
                bridge.Wiki, "_llm_call", return_value="should not appear"):
            out = bridge.handle("? риск по сделке BluePeak Energy",
                                wiki=self.wiki, state=self._state("employee"))
        self.assertNotIn(bridge.RECS_MARKER, out)

    def test_llm_failure_keeps_the_answer_intact(self) -> None:
        with self._enabled(), mock.patch.object(
                bridge.Wiki, "_llm_call", side_effect=OSError("api down")):
            out = bridge.handle("? мой день", wiki=self.wiki, state=self._state())
        self.assertNotIn(bridge.RECS_MARKER, out)
        self.assertIn("My Day", out)  # deterministic answer unharmed


class Autoplay(unittest.TestCase):
    """`демо старт` runs the presenter script hands-free: the bridge posts a
    narrator comment, the command (▶️-prefixed so the poll loop never
    re-processes it) and the answer, beat by beat; `демо стоп` halts it."""

    def setUp(self) -> None:
        self.wiki = bridge.Wiki()
        self.state = {"role": "employee", "trigger": "?"}

    def test_demo_start_returns_autoplay_directive_with_default_delay(self) -> None:
        out = bridge.handle("демо старт", wiki=self.wiki, state=self.state)
        self.assertIsInstance(out, dict)
        self.assertEqual(out["autoplay"], 10)

    def test_demo_start_accepts_a_custom_delay(self) -> None:
        out = bridge.handle("demo start 5", wiki=self.wiki, state=self.state)
        self.assertEqual(out["autoplay"], 5)

    def test_demo_stop_sets_the_stop_event(self) -> None:
        self.wiki.autoplay_stop.clear()
        out = bridge.handle("демо стоп", wiki=self.wiki, state=self.state)
        self.assertIsInstance(out, str)
        self.assertTrue(self.wiki.autoplay_stop.is_set())

    def test_every_scripted_command_is_understood(self) -> None:
        # Replay the script exactly like run_autoplay does (with {pid}
        # substitution); every command must route — never "didn't understand".
        pid = "1"
        for comment, command in bridge.AUTOPLAY_SCRIPT:
            self.assertTrue(comment, "every beat needs a narrator comment")
            if not command:
                continue
            reply = bridge.handle(command.format(pid=pid), wiki=self.wiki, state=self.state)
            if isinstance(reply, dict):
                self.assertIn("upload", reply, f"beat {command!r} returned an odd dict")
                continue
            self.assertIsInstance(reply, str, f"beat {command!r} must reply with text")
            self.assertNotIn("didn't understand", reply, f"beat {command!r} not routed")
            found = bridge.re.findall(r"proposal-0*(\d+)", reply)
            if found:
                pid = found[-1]

    def test_run_autoplay_posts_comments_commands_answers_and_uploads(self) -> None:
        class FakeRC:
            def __init__(self) -> None:
                self.posts: list[str] = []
                self.uploads: list[str] = []

            def post(self, room_id: str, text: str) -> None:  # noqa: ARG002
                self.posts.append(text)

            def upload(self, room_id: str, filename: str, content: bytes,
                       ctype: str, caption: str = "") -> dict:  # noqa: ARG002
                self.uploads.append(f"{filename} ({ctype})")
                return {"success": True}

        rc = FakeRC()
        bridge.run_autoplay(rc, "room", self.wiki, self.state, delay=0)
        joined = "\n".join(rc.posts)
        self.assertIn("🎙️", joined)
        self.assertIn("▶️ `роль: marketing`", joined)
        self.assertIn("Solara Hospitality", joined)  # the story beats ride along
        self.assertIn("🏁", rc.posts[-1])
        self.assertTrue(any("image/png" in u for u in rc.uploads),
                        "the chart beat must upload a PNG")

    def test_run_autoplay_honors_stop(self) -> None:
        class FakeRC:
            def __init__(self, wiki: "bridge.Wiki") -> None:
                self.posts: list[str] = []
                self._wiki = wiki

            def post(self, room_id: str, text: str) -> None:  # noqa: ARG002
                self.posts.append(text)
                self._wiki.autoplay_stop.set()  # user types `демо стоп` mid-run

        rc = FakeRC(self.wiki)
        bridge.run_autoplay(rc, "room", self.wiki, self.state, delay=0)
        self.assertLess(len(rc.posts), 8, "must halt at the next beat after stop")
        self.assertIn("⏹", rc.posts[-1])


class SummaryMarker(unittest.TestCase):
    """The live smoke test checks for the summary headline; it must share the
    marker with bridge._summary_line — a hard-coded '🤖 Сводка' literal went
    dead when the header became '🤖 Summary (from card data):'."""

    def test_answer_carries_the_shared_marker(self) -> None:
        wiki = bridge.Wiki()
        out = bridge.handle("? пайплайн", wiki=wiki,
                            state={"role": "head-of-sales", "trigger": "?",
                                   "company_name": "BluePeak Energy",
                                   "company_id": "demo-company-bluepeak-energy"})
        self.assertIn(bridge.SUMMARY_MARKER, out)

    def test_smoke_test_uses_the_shared_marker(self) -> None:
        src = (ROOT / "integrations" / "rocketchat" / "smoke_test.py").read_text(encoding="utf-8")
        self.assertIn("SUMMARY_MARKER", src, "smoke test must check the shared marker constant")
        self.assertNotIn("🤖 Сводка", src, "dead hard-coded marker must be gone")


class ClearHistory(unittest.TestCase):
    def test_clear_requires_explicit_confirmation(self) -> None:
        out = bridge.handle("очистить историю", wiki=None, state={"role": "employee", "trigger": "?"})
        self.assertIsInstance(out, str)
        self.assertIn("Confirm", out)

    def test_clear_with_confirmation_returns_signal(self) -> None:
        out = bridge.handle("очистить историю да", wiki=None, state={"role": "employee", "trigger": "?"})
        self.assertEqual(out, {"clear_history": True})

    def test_clearance_lookalike_does_not_trigger_reset(self) -> None:
        # "clearance ..." must NOT be swallowed by the destructive `clear` command.
        wiki = bridge.Wiki()
        out = bridge.handle("clearance report for Atlas Foods",
                            wiki=wiki, state={"role": "employee", "trigger": "?",
                                              "company_name": "Atlas Foods"})
        self.assertNotEqual(out, {"clear_history": True})
        if isinstance(out, str):
            self.assertNotIn("delete the ENTIRE chat history", out)

    def test_clear_english_confirmation_returns_signal(self) -> None:
        out = bridge.handle("clear history yes", wiki=None, state={"role": "employee", "trigger": "?"})
        self.assertEqual(out, {"clear_history": True})

    def test_sweep_pages_and_deletes_every_message(self) -> None:
        rc = bridge.RocketChat("http://x", "u", "p")
        pages = [
            {"success": True, "messages": [{"_id": "m3", "ts": "2026-01-03"}, {"_id": "m2", "ts": "2026-01-02"}]},
            {"success": True, "messages": [{"_id": "m1", "ts": "2026-01-01"}]},
            {"success": True, "messages": []},
        ]
        deleted_ids: list[str] = []
        hist_calls = {"n": 0}

        def fake_call(path: str, data: dict | None = None) -> dict:
            if "history" in path:
                page = pages[min(hist_calls["n"], len(pages) - 1)]
                hist_calls["n"] += 1
                return page
            if "chat.delete" in path:
                deleted_ids.append(data["msgId"])
                return {"success": True}
            return {"success": False}

        rc._call = fake_call
        deleted, skipped = rc.clear_history("im", "room1")
        self.assertEqual((deleted, skipped), (3, 0))
        self.assertEqual(set(deleted_ids), {"m1", "m2", "m3"})

    def test_sweep_counts_undeletable_as_skipped(self) -> None:
        rc = bridge.RocketChat("http://x", "u", "p")
        pages = [{"success": True, "messages": [{"_id": "a", "ts": "2"}, {"_id": "b", "ts": "1"}]},
                 {"success": True, "messages": []}]
        hist_calls = {"n": 0}

        def fake_call(path: str, data: dict | None = None) -> dict:
            if "history" in path:
                page = pages[min(hist_calls["n"], len(pages) - 1)]
                hist_calls["n"] += 1
                return page
            return {"success": False, "http": 403}  # no permission to delete

        rc._call = fake_call
        deleted, skipped = rc.clear_history("im", "room1")
        self.assertEqual((deleted, skipped), (0, 2))


if __name__ == "__main__":
    unittest.main()
