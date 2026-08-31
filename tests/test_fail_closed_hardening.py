"""Deny-on-doubt hardening (security review 2026-07-04, findings #6 and #10).

Two chokepoints silently failed OPEN on an unexpected input:
- policy._base_decision granted the whole boundary for any attribute_constraints
  value it did not literally recognize (a typo or a future/renamed constraint) —
  an operator narrowing the code does not implement must deny, not open (#6).
- vault_guard.is_demo_vault skipped a card it could not read, so an unreadable
  `dataset: production` card no longer disqualified the vault, letting the
  fixture-identity gateway serve the readable remainder (#10).
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp import vault_guard  # noqa: E402
from saleswiki_mcp.identity import Actor  # noqa: E402
from saleswiki_mcp.policy import PolicyEvaluator, Resource  # noqa: E402


class PolicyUnknownConstraintFailsClosed(unittest.TestCase):
    """An unrecognized attribute_constraints value must block, not grant-all."""

    def _policy(self, constraint: str) -> dict:
        return {
            "roles": [{
                "id": "sales",
                "boundaries": ["broad", "sales-confidential"],
                "attribute_constraints": {"sales-confidential": constraint},
            }],
            "rules": {},
        }

    def setUp(self) -> None:
        # An SDR-like actor who owns nothing, against another team's record.
        self.actor = Actor(id="u1", role="sales", team="west", owns=())
        self.resource = Resource(entity_id="d1", boundary="sales-confidential",
                                 owner="someone-else", team="east", company="acme")

    def test_typo_constraint_blocks(self) -> None:
        pe = PolicyEvaluator(self._policy("assigned "))  # trailing space
        self.assertEqual(pe.can_read(self.actor, self.resource).effect, "block")

    def test_future_constraint_blocks(self) -> None:
        pe = PolicyEvaluator(self._policy("team_only"))  # not yet implemented
        self.assertEqual(pe.can_read(self.actor, self.resource).effect, "block")

    def test_recognized_assigned_still_blocks_non_owner(self) -> None:
        # Regression: the known 'assigned' constraint keeps blocking a non-owner.
        pe = PolicyEvaluator(self._policy("assigned"))
        self.assertEqual(pe.can_read(self.actor, self.resource).effect, "block")

    def test_no_constraint_still_grants_the_boundary(self) -> None:
        # Regression: an unconstrained role (no attribute_constraints key) is still
        # allowed the boundary it lists — line 91 stays correct for the None case.
        policy = {"roles": [{"id": "sales", "boundaries": ["broad", "sales-confidential"]}], "rules": {}}
        pe = PolicyEvaluator(policy)
        self.assertEqual(pe.can_read(self.actor, self.resource).effect, "allow")


class DemoVaultUnreadableCardFailsClosed(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = Path(tempfile.mkdtemp(prefix="demo-guard-"))
        (self.vault / "Company - Demo.md").write_text(
            "---\ndataset: demo\nsynthetic: true\n---\n# Demo\n", encoding="utf-8"
        )

    def test_unreadable_production_card_fails_closed(self) -> None:
        # A disqualifying `dataset: production` card that cannot be read (here a
        # dangling symlink; equally a permissions/IO error) must not be silently
        # skipped — the vault must be treated as not-demo.
        link = self.vault / "Company - Real.md"
        link.symlink_to(self.vault / "does-not-exist-target.md")
        self.assertFalse(vault_guard.is_demo_vault(self.vault),
                         "an unreadable card must fail closed, not be skipped")

    def test_non_utf8_card_does_not_crash_and_fails_closed(self) -> None:
        # A non-UTF-8 card raises UnicodeDecodeError (a ValueError, not OSError);
        # it must be handled as fail-closed, never crash the guard.
        (self.vault / "Company - Binary.md").write_bytes(b"\xff\xfe dataset: production")
        self.assertFalse(vault_guard.is_demo_vault(self.vault))

    def test_all_readable_demo_vault_still_passes(self) -> None:
        # Regression: a fully readable demo vault is still recognized.
        self.assertTrue(vault_guard.is_demo_vault(self.vault))


if __name__ == "__main__":
    unittest.main()
