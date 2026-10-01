#!/usr/bin/env python3
"""Render an optional-LLM system prompt without calling a model or reading vault data.

Use this while editing schemas/presentation-profiles.json:
  python3 scripts/render_presentation_prompt.py --role marketing --task campaign_brief \
    --verbosity compact --tone analytical --focus audience
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations" / "rocketchat"))

from _bridge_presentation import PreferenceError, PresentationProfiles  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a SalesWiki optional-LLM presentation prompt")
    parser.add_argument("--role", required=True, help="Presentation role, for example marketing")
    parser.add_argument("--task", required=True, help="Answer product, for example campaign_brief")
    parser.add_argument("--verbosity", default="standard", choices=("compact", "standard"))
    parser.add_argument("--tone", default="direct", choices=("direct", "analytical"))
    parser.add_argument("--focus", default="", choices=("", "next_action", "evidence", "risks", "audience"))
    parser.add_argument("--instruction", default="", help="Optional wording preference, never an access instruction")
    args = parser.parse_args()
    profiles = PresentationProfiles()
    try:
        preferences = profiles.update(None, "verbosity", args.verbosity)
        preferences = profiles.update(preferences, "tone", args.tone)
        if args.focus:
            preferences = profiles.update(preferences, "focus", args.focus)
        if args.instruction:
            preferences = profiles.update(preferences, "custom_instruction", args.instruction)
    except PreferenceError as exc:
        parser.error(str(exc))
    print(profiles.system_prompt(args.role, args.task, preferences))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
