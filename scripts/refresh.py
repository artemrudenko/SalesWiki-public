#!/usr/bin/env python3
"""One-command SalesWiki refresh: health check, indexes, dashboard snapshots.

Replaces the manual three-command loop:

    python3 scripts/refresh.py            # production contour
    python3 scripts/refresh.py --demo     # demo contour (synthetic data)
    python3 scripts/refresh.py --dry-run  # print steps without running

Standard library only. Stops on the first failing step and exits non-zero,
so it can be used as the single post-edit validation command.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"

CONTOURS = ("production", "demo")


@dataclass(frozen=True)
class Step:
    title: str
    command: list[str]


def build_steps(contour: str) -> list[Step]:
    """Return the ordered refresh steps for a contour."""
    if contour not in CONTOURS:
        raise ValueError(f"Unknown contour: {contour!r}. Expected one of {CONTOURS}.")

    health = Step(
        title="Health check",
        command=[sys.executable, str(SCRIPTS / "health_check.py")],
    )

    if contour == "demo":
        demo_vault = PROJECT_ROOT / "demo" / "demo-vault"
        demo_indexes = PROJECT_ROOT / "demo" / "indexes"
        demo_snapshots = PROJECT_ROOT / "demo" / "reports" / "dashboard-snapshots"
        indexes = Step(
            title="Build demo indexes",
            command=[
                sys.executable,
                str(SCRIPTS / "build_indexes.py"),
                "--source-root",
                str(demo_vault),
                "--output-root",
                str(demo_indexes),
                "--no-update-state",
            ],
        )
        snapshots = Step(
            title="Build demo dashboard snapshots",
            command=[
                sys.executable,
                str(SCRIPTS / "build_dashboard_snapshots.py"),
                "--index-root",
                str(demo_indexes),
                "--output-root",
                str(demo_snapshots),
                "--vault-root",
                str(demo_vault),
            ],
        )
    else:
        indexes = Step(
            title="Build indexes",
            command=[sys.executable, str(SCRIPTS / "build_indexes.py")],
        )
        snapshots = Step(
            title="Build dashboard snapshots",
            command=[sys.executable, str(SCRIPTS / "build_dashboard_snapshots.py")],
        )

    return [health, indexes, snapshots]


def run_steps(steps: list[Step], dry_run: bool) -> int:
    for index, step in enumerate(steps, start=1):
        rendered = " ".join(step.command)
        print(f"[{index}/{len(steps)}] {step.title}", flush=True)
        print(f"    {rendered}", flush=True)
        if dry_run:
            continue
        result = subprocess.run(step.command, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"FAILED: {step.title} (exit {result.returncode})", file=sys.stderr)
            return result.returncode
    print("Refresh complete." if not dry_run else "Dry run complete; nothing executed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Refresh the demo contour (demo/demo-vault -> demo/indexes -> demo/reports).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned steps without executing them.",
    )
    args = parser.parse_args()
    contour = "demo" if args.demo else "production"
    print(f"SalesWiki refresh ({contour} contour)", flush=True)
    return run_steps(build_steps(contour), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
