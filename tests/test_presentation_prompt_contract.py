"""Regression contract for the optional LLM presentation prompt layer.

These tests do not call a model. They prove that role/task profiles and user
preferences compose predictably and that a preference cannot ask to weaken the
visible Answer Contract.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations" / "rocketchat"))

from _bridge_presentation import PreferenceError, PresentationProfiles  # noqa: E402


class PresentationPromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = ROOT / "tests" / "fixtures" / "presentation-prompt-scenarios.json"
        cls.contract = json.loads(fixture.read_text(encoding="utf-8"))
        cls.profiles = PresentationProfiles()

    def test_synthetic_role_task_scenarios_preserve_invariants(self) -> None:
        for scenario in self.contract["scenarios"]:
            prompt = self.profiles.system_prompt(
                scenario["role"], scenario["task"], scenario["preferences"]
            )
            for fragment in scenario["must_include"] + scenario["must_include_in_every_prompt"]:
                self.assertIn(fragment, prompt, scenario["id"])

    def test_untrusted_personal_instruction_cannot_weaken_access_or_provenance(self) -> None:
        for instruction in self.contract["rejected_instructions"]:
            with self.assertRaises(PreferenceError, msg=instruction):
                self.profiles.update(None, "custom_instruction", instruction)

    def test_unknown_role_gets_only_the_safe_default_presentation(self) -> None:
        prompt = self.profiles.system_prompt("unknown-role", "deal_risk", None)
        self.assertIn("Role: unknown-role. Task: deal_risk.", prompt)
        self.assertIn("Use only facts from the supplied Answer Contract.", prompt)
        self.assertNotIn("Role presentation:", prompt)


if __name__ == "__main__":
    unittest.main()
