"""Phase 2 tests: permissioned demo sub-vault generation.

The permissioned demo proves role-aware boundaries on synthetic data. It must
stay isolated under demo/permissioned/<boundary>/ and never contaminate
production. Run with: python3 -m unittest discover -s tests
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
from saleswiki_mcp import config  # noqa: E402

# Recognizable sales-confidential strings that must never appear in broad cards.
SALES_SECRETS = ("Discount floor", "Pricing:", "ACV")
# Recognizable call-confidential strings that must never appear in broad cards.
CALL_SECRETS = ("internal budget", "RivalCorp")


class PermissionedDemoGeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="perm-demo-"))
        gdv.generate_permissioned_demo(self.tmp)
        self.md_files = sorted(self.tmp.rglob("*.md"))

    def test_boundary_folders_exist(self) -> None:
        for boundary in ("broad", "sales-confidential", "personal-data"):
            self.assertTrue((self.tmp / boundary).is_dir(), f"missing boundary folder {boundary}")

    def test_three_broad_company_cards(self) -> None:
        broad_companies = sorted((self.tmp / "broad").rglob("Company - *.md"))
        self.assertGreaterEqual(len(broad_companies), 3)

    def test_bluepeak_has_salesconf_and_personal_data(self) -> None:
        salesconf = list((self.tmp / "sales-confidential").rglob("*BluePeak*"))
        pdata = list((self.tmp / "personal-data").rglob("*BluePeak*")) or list(
            (self.tmp / "personal-data").rglob("*bluepeak*")
        )
        self.assertTrue(salesconf, "BluePeak must have a sales-confidential card")
        self.assertTrue(pdata, "BluePeak must have a personal-data reference")

    def test_frontmatter_dates_use_today_for_honest_freshness(self) -> None:
        # Demo cards are labeled freshness: fresh. For that to be honest rather
        # than misleading weeks after generation, their review dates must be the
        # date the vault was generated, not a frozen past constant.
        from datetime import date

        today = date.today().isoformat()
        blob = "\n".join(p.read_text(encoding="utf-8") for p in self.md_files)
        self.assertIn(f"updated: {today}", blob, "cards must be stamped with today's date")
        self.assertNotIn("updated: 2026-05-30", blob, "no frozen update date")
        self.assertNotIn("last_reviewed: 2026-05-30", blob, "no frozen review date")

    def test_all_cards_are_synthetic_demo(self) -> None:
        self.assertTrue(self.md_files, "no markdown generated")
        for path in self.md_files:
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(self.tmp)
            self.assertIn("dataset: demo", text, f"{rel} missing dataset: demo")
            self.assertIn("synthetic: true", text, f"{rel} missing synthetic: true")
            self.assertIn("entity_id: demo-", text, f"{rel} missing demo- entity_id")

    def test_card_boundary_matches_folder(self) -> None:
        for path in self.md_files:
            rel = path.relative_to(self.tmp)
            boundary = rel.parts[0]
            self.assertIn(f"boundary: {boundary}", path.read_text(encoding="utf-8"), f"{rel} boundary mismatch")

    def test_no_salesconf_secret_leaks_into_broad(self) -> None:
        for path in (self.tmp / "broad").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for secret in SALES_SECRETS:
                self.assertNotIn(secret, text, f"sales secret '{secret}' leaked into broad card {path.name}")

    def test_personal_data_has_no_raw_transcript_body(self) -> None:
        # Registry contract (schemas/boundary-registry.json: raw_bodies_allowed
        # false): personal-data cards hold contact handles/metadata and at most a
        # clearly-marked SANITIZED extract — never a speaker-attributed raw
        # transcript, raw quote or unredacted figure.
        pd_cards = sorted((self.tmp / "personal-data").rglob("*.md"))
        self.assertTrue(pd_cards, "personal-data boundary must hold reference cards")
        for path in pd_cards:
            text = path.read_text(encoding="utf-8")
            self.assertIn("restricted://", text, "personal-data card must carry an opaque handle")
            self.assertNotIn("Raw Transcript", text, f"{path.name} must not embed the raw transcript body")
            self.assertNotIn("Keep that between us", text, f"raw quote leaked into {path.name}")
            self.assertNotIn("$200-240k", text, f"unredacted budget figure leaked into {path.name}")
            self.assertNotIn("Dana Reyes", text, f"contact identity leaked into {path.name}")
            self.assertIn("SANITIZED", text, f"{path.name} must keep a clearly-marked sanitized extract")

    def test_salesconf_call_cards_cover_the_hero_accounts_and_dense_graph_fixture(self) -> None:
        calls = sorted((self.tmp / "sales-confidential").rglob("Call - *.md"))
        self.assertGreaterEqual(len(calls), 8, "hero accounts and the dense graph fixture need sales-confidential call cards")

    def test_call_card_is_sanitized_and_keeps_raw_as_handle(self) -> None:
        for path in (self.tmp / "sales-confidential").rglob("Call - *.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("type: call", text, f"{path.name} must be a call card")
            self.assertIn("Sanitized takeaway", text, f"{path.name} must carry a sanitized conclusion marker")
            self.assertIn("restricted://", text, f"{path.name} must reference the raw transcript as an opaque handle")

    def test_call_secrets_never_leak_into_broad(self) -> None:
        for path in (self.tmp / "broad").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for secret in CALL_SECRETS:
                self.assertNotIn(secret, text, f"call secret '{secret}' leaked into broad card {path.name}")


    def test_every_company_has_a_broad_lead_card(self) -> None:
        leads = sorted((self.tmp / "broad").rglob("Lead - *.md"))
        # 7 sales-qualified hero accounts + 4 top-of-funnel prospects + the
        # dense Workbench graph fixture.
        self.assertGreaterEqual(len(leads), 12, "hero leads, prospect leads and dense fixture expected")
        stages = []
        for path in leads:
            text = path.read_text(encoding="utf-8")
            self.assertIn("type: lead", text, f"{path.name} must be a lead card")
            self.assertIn("Score band", text, f"{path.name} must carry a score band")
            self.assertIn("Funnel stage", text, f"{path.name} must carry a funnel stage")
            self.assertIn("restricted://", text, f"{path.name} must reference the contact as a handle")
            stages.append(text)
        blob = "\n".join(stages)
        # The funnel spans marketing (MQL/nurture) and sales (SQL).
        self.assertIn("Funnel stage: SQL", blob)
        self.assertIn("Funnel stage: MQL", blob)
        self.assertIn("Funnel stage: nurture", blob)

    def test_broad_event_card_lists_target_accounts(self) -> None:
        event = self.tmp / "broad" / "wiki" / "entities" / "events" / "Event - Sales Tech Summit 2026.md"
        self.assertTrue(event.is_file(), "the broad target-account event must exist")
        text = event.read_text(encoding="utf-8")
        self.assertIn("type: event", text)
        for name in ("BluePeak Energy", "Northstar Robotics", "Atlas Foods"):
            self.assertIn(name, text, f"event card must list {name} as a target account")

    def test_call_secrets_never_leak_into_broad_lead_or_event(self) -> None:
        for path in (self.tmp / "broad").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for secret in SALES_SECRETS + CALL_SECRETS:
                self.assertNotIn(secret, text, f"secret '{secret}' leaked into broad card {path.name}")


class PermissionedDemoStoryAccounts(unittest.TestCase):
    """The two new hero accounts and the intent prospect must carry their key
    story facts in the right boundary: the renewal-save trigger (Solara), the
    quantified case-study proof (Ironclad) and the switched-vendor intent
    (Cinder) — with no new transcript secret leaking anywhere."""

    # Raw-transcript-only phrases from the new accounts: generator input,
    # never allowed on any card in any boundary.
    NEW_TRANSCRIPT_SECRETS = ("calling our GM weekly", "budget approved up to $400k")

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="perm-demo-story-"))
        gdv.generate_permissioned_demo(self.tmp)
        self.md_files = sorted(self.tmp.rglob("*.md"))

    def _read(self, *parts: str) -> str:
        path = self.tmp.joinpath(*parts)
        self.assertTrue(path.is_file(), f"missing card {path.relative_to(self.tmp)}")
        return path.read_text(encoding="utf-8")

    def test_solara_renewal_at_risk_deal(self) -> None:
        deal = self._read("sales-confidential", "wiki", "entities", "deals",
                          "Deal - Solara Hospitality - Pilot.md")
        self.assertIn("left the company", deal, "risk must name the champion departure")
        self.assertIn("renewal", deal.lower(), "risk must name the renewal window")
        self.assertIn("Win probability: 25%", deal, "renewal-at-risk deal must carry a low win probability")
        self.assertIn("executive business review", deal, "action must book an EBR")
        self.assertIn("multi-thread", deal, "action must multi-thread to the new stakeholder")

    def test_solara_champion_departure_is_a_broad_market_signal(self) -> None:
        signal = self._read("broad", "wiki", "entities", "sources",
                            "Source - Solara Hospitality Leadership Change.md")
        self.assertIn("Director of Guest Operations", signal)
        self.assertIn("left the company", signal, "the leadership-change signal is the public trigger")

    def test_solara_competitor_courting_is_sales_confidential(self) -> None:
        intel = self._read("sales-confidential", "wiki", "entities", "competitor-intel",
                           "Competitor Intel - Solara Hospitality - StayCentric.md")
        self.assertIn("StayCentric", intel)

    def test_ironclad_quantified_proof_in_broad_private_case(self) -> None:
        case = self._read("broad", "wiki", "entities", "private-cases",
                          "Private Case - Ironclad Freight - Sanitized ROI Proof.md")
        self.assertIn("dock-to-stock time by 22%", case, "marketing needs the measured pilot result")
        self.assertIn("12 analyst-hours per week", case)
        self.assertIn("reference", case, "the customer agreed to be a reference")

    def test_ironclad_expansion_deal_is_open_with_decent_odds(self) -> None:
        deal = self._read("sales-confidential", "wiki", "entities", "deals",
                          "Deal - Ironclad Freight - Pilot.md")
        self.assertIn("Win probability: 65%", deal)
        self.assertIn("expansion", deal.lower(), "the open deal is the multi-site expansion")

    def test_ironclad_network_expansion_signal_is_broad(self) -> None:
        signal = self._read("broad", "wiki", "entities", "sources",
                            "Source - Ironclad Freight Network Expansion.md")
        self.assertIn("distribution centers", signal)

    def test_cinder_prospect_has_intent_signal_and_no_deal(self) -> None:
        lead = self._read("broad", "wiki", "entities", "leads", "Lead - Cinder Analytics.md")
        self.assertIn("Score band: hot", lead)
        signal = self._read("broad", "wiki", "entities", "sources",
                            "Source - Cinder Analytics Vendor-Switch Intent.md")
        self.assertIn("G2 review", signal, "the switched-vendor intent is the marketing trigger")
        self.assertIn("RFP", signal)
        for boundary in ("sales-confidential", "personal-data"):
            hits = list((self.tmp / boundary).rglob("*Cinder*"))
            self.assertFalse(hits, f"prospect must have no {boundary} cards: {hits}")

    def test_new_transcript_secrets_never_land_on_any_card(self) -> None:
        for path in self.md_files:
            text = path.read_text(encoding="utf-8")
            for secret in self.NEW_TRANSCRIPT_SECRETS:
                self.assertNotIn(secret, text,
                                 f"raw transcript phrase '{secret}' leaked into {path.name}")


class DemoVaultDateCoherence(unittest.TestCase):
    """Forward-looking demo fields must stay today-or-future. Cards are stamped
    'fresh' with last_reviewed = today; a next_review/next_check/close date in
    the past would contradict that on the flagship 'today' dashboard."""

    def test_forward_dates_are_today_or_future(self) -> None:
        import re
        from datetime import date

        tmp = Path(tempfile.mkdtemp(prefix="demo-dates-"))
        gdv.generate(tmp, reset=False)
        today = date.today().isoformat()
        forward = ("next_review", "next_check", "close_date", "due")
        offenders = []
        for md in tmp.rglob("*.md"):
            for line in md.read_text(encoding="utf-8").splitlines():
                for field in forward:
                    if line.startswith(f"{field}: "):
                        value = line.split(": ", 1)[1].strip()
                        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) and value < today:
                            offenders.append(f"{md.name}: {field}={value}")
        self.assertFalse(offenders, f"past forward-dates on fresh cards: {offenders}")


class PermissionedFixtures(unittest.TestCase):
    def test_hos_fixture_exists(self) -> None:
        users = config.identity_config()["providers"]["fixture"]["users"]
        elena = next((u for u in users if u["id"] == "demo-elena-hos"), None)
        self.assertIsNotNone(elena, "demo-elena-hos HoS fixture must exist")
        self.assertEqual(elena["role"], "hos")


if __name__ == "__main__":
    unittest.main()
