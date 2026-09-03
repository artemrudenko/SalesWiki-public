#!/usr/bin/env python3
"""Generate sample role digests from the synthetic permissioned demo vault.

Produces the "what lands in your inbox every morning" artifacts for demos:
Markdown digests rendered by the same Answer Contract the MCP gateway uses,
one per persona. Output is deterministic (fixed as-of timestamp matching the
demo dataset), so regenerated files only change when the demo data changes.

    python3 scripts/generate_demo_digests.py
    python3 scripts/generate_demo_digests.py --output-root /tmp/digests

Standard library only; reads demo/permissioned, never writes outside the
output root (audit/proposal sinks go to a temp directory).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp import config  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

DEMO_VAULT = ROOT / "demo" / "permissioned"
DEFAULT_OUTPUT = ROOT / "demo" / "reports" / "digests"

# Anchor the audit "now" to the generation date so it tracks the freshly stamped
# demo cards (which use today's date). Freshness/as-of in the rendered digest are
# derived from the cards themselves, so this only timestamps the audit sink.
DEMO_NOW = date.today().isoformat() + "T00:00:00Z"

BANNER = (
    "> Synthetic demo data (`dataset: demo`) — safe to share. "
    "Regenerate with `python3 scripts/generate_demo_digests.py`.\n"
)

DIGESTS = [
    {
        "file": "my-day-ae.md",
        "actor": "demo-ethan-ae",
        "persona": "Account Executive (Ethan)",
        "tool": "my_day",
        "intro": "What an AE finds in the inbox before the first call:",
    },
    {
        "file": "my-day-marketing.md",
        "actor": "demo-olivia-marketing",
        "persona": "Marketing (Olivia)",
        "tool": "my_day",
        "intro": "The same digest for marketing — deal economics stay invisible:",
    },
    {
        "file": "pipeline-digest-hos.md",
        "actor": "demo-claire-hos",
        "persona": "Head of Sales (Claire)",
        "tool": "pipeline_risk_digest",
        "intro": "The weekly-review view for the Head of Sales:",
    },
]


def generate(output_root: Path) -> list[Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="demo-digests-runtime-") as tmp:
        sinks = Path(tmp)
        service = build_default_service(
            DEMO_VAULT,
            sinks / "audit.jsonl",
            sinks / "proposals.jsonl",
            now=lambda: DEMO_NOW,
        )
        for spec in DIGESTS:
            actor = FixtureIdentityProvider(
                spec["actor"], config.identity_config()
            ).resolve()
            envelope = getattr(service, spec["tool"])(actor)
            path = output_root / spec["file"]
            path.write_text(
                "\n".join(
                    [
                        f"# Morning Digest — {spec['persona']}",
                        "",
                        BANNER,
                        spec["intro"],
                        "",
                        "---",
                        "",
                        envelope["text"],
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            written.append(path)

    index = output_root / "index.md"
    lines = [
        "# Demo Digests",
        "",
        BANNER,
        "Delivery-format examples of what each role receives without opening",
        "Obsidian or a terminal (Slack/email style). Generated from the",
        "permissioned demo vault by the same Answer Contract as the MCP gateway.",
        "",
    ]
    for spec in DIGESTS:
        lines.append(f"- [{spec['persona']}]({spec['file']}) — `{spec['tool']}`")
    lines.append("")
    index.write_text("\n".join(lines), encoding="utf-8")
    written.append(index)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT),
        help="Directory for generated digests.",
    )
    args = parser.parse_args()
    written = generate(Path(args.output_root))
    print("SalesWiki demo digests")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
