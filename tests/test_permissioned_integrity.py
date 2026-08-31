"""Arch #2/#5/#11 tests: referential + ownership + boundary integrity.

The generated permissioned demo must satisfy the integrity invariants, and the
health_check guard must actually catch violations (a boundary that disagrees with
its folder, a dangling company reference, or an owner/team off the org roster) -
so an access-relevant typo cannot pass silently.
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
import health_check  # noqa: E402


def integrity_findings(perm_root: Path, registry: dict | None = None):
    findings: list = []
    health_check.check_permissioned_data_integrity(findings, perm_root=perm_root, registry=registry)
    return [f.message for f in findings]


class PermissionedIntegrity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="integrity-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.deal = self.vault / "sales-confidential" / "wiki" / "entities" / "deals" / "Deal - BluePeak Energy - Pilot.md"

    def test_generated_demo_is_clean(self) -> None:
        self.assertEqual(integrity_findings(self.vault), [], "generated demo must satisfy integrity invariants")

    def test_boundary_folder_mismatch_is_caught(self) -> None:
        text = self.deal.read_text(encoding="utf-8").replace("boundary: sales-confidential", "boundary: broad")
        self.deal.write_text(text, encoding="utf-8")
        self.assertTrue(any("disagrees with its folder" in m for m in integrity_findings(self.vault)))

    def test_dangling_company_reference_is_caught(self) -> None:
        text = self.deal.read_text(encoding="utf-8").replace("company: demo-company-bluepeak-energy", "company: demo-company-ghost")
        self.deal.write_text(text, encoding="utf-8")
        self.assertTrue(any("does not resolve to a known company" in m for m in integrity_findings(self.vault)))

    def test_owner_off_roster_is_caught(self) -> None:
        text = self.deal.read_text(encoding="utf-8").replace("owner: demo-ivan-ae", "owner: demo-ivann-ae")
        self.deal.write_text(text, encoding="utf-8")
        self.assertTrue(any("owner: demo-ivann-ae" in m and "org roster" in m for m in integrity_findings(self.vault)))

    def test_team_typo_is_caught(self) -> None:
        text = self.deal.read_text(encoding="utf-8").replace("team: sales-west", "team: sales_west")
        self.deal.write_text(text, encoding="utf-8")
        self.assertTrue(any("team: sales_west" in m and "org roster" in m for m in integrity_findings(self.vault)))

    def test_misfiled_card_outside_known_prefix_is_caught(self) -> None:
        """A card outside every path_map prefix would fail closed (quarantine);
        the health check must surface it so it gets filed, not silently hidden."""
        stray = self.vault / "partners" / "Deal - Misfiled.md"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("---\ntype: deal\n---\n\nbody\n", encoding="utf-8")
        self.assertTrue(
            any("outside every known boundary prefix" in m for m in integrity_findings(self.vault)),
            "a misfiled card must be flagged as outside the known boundary prefixes",
        )

    # FINDING 5: a registry whose default_boundary equals a legitimately mapped
    # boundary must not flag every card in that boundary — only genuine
    # no-prefix-match is an error.
    LEGACY_BROAD_REGISTRY: dict = {
        "default_boundary": "broad",
        "boundaries": [
            {"id": "broad", "label": "Broad vault", "sensitivity": "internal"},
            {"id": "sales-confidential", "label": "Sales-confidential", "sensitivity": "sales-confidential"},
            {"id": "personal-data", "label": "Personal-data store", "sensitivity": "personal-data",
             "raw_bodies_allowed": False},
        ],
        "path_map": [
            {"prefix": "broad/", "boundary": "broad"},
            {"prefix": "sales-confidential/", "boundary": "sales-confidential"},
            {"prefix": "personal-data/", "boundary": "personal-data"},
        ],
    }

    def test_default_boundary_equal_to_mapped_boundary_is_not_flagged(self) -> None:
        messages = integrity_findings(self.vault, registry=self.LEGACY_BROAD_REGISTRY)
        self.assertFalse(
            [m for m in messages if "outside every known boundary prefix" in m],
            "cards whose prefix maps to the default boundary must not be treated as unmapped",
        )

    def test_genuine_no_match_is_still_caught_with_default_equal_to_mapped(self) -> None:
        stray = self.vault / "partners" / "Deal - Misfiled.md"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("---\ntype: deal\n---\n\nbody\n", encoding="utf-8")
        messages = integrity_findings(self.vault, registry=self.LEGACY_BROAD_REGISTRY)
        self.assertTrue(
            any("outside every known boundary prefix" in m for m in messages),
            "a genuinely unmapped card must still be flagged even when default == a mapped boundary",
        )

    # FINDING 4: enforce the registry's raw_bodies_allowed contract so a raw
    # transcript can never silently reappear inside a personal-data card.
    def test_raw_transcript_in_no_raw_bodies_boundary_is_caught(self) -> None:
        pd_card = next(iter(sorted((self.vault / "personal-data").rglob("*.md"))))
        pd_card.write_text(
            pd_card.read_text(encoding="utf-8")
            + "\n## Raw Transcript (personal-data)\n\nAE (Ivan Petrov): full raw dialogue here\n",
            encoding="utf-8",
        )
        self.assertTrue(
            any("raw_bodies_allowed" in m for m in integrity_findings(self.vault)),
            "a raw-transcript section in a raw_bodies_allowed:false boundary must be an ERROR",
        )

    def test_generated_personal_data_cards_pass_raw_bodies_check(self) -> None:
        self.assertFalse(
            [m for m in integrity_findings(self.vault) if "raw_bodies_allowed" in m],
            "the generated demo must satisfy the raw-bodies contract",
        )


if __name__ == "__main__":
    unittest.main()
