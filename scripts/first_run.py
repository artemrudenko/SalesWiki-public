#!/usr/bin/env python3
"""First-run assistant for the public SalesWiki demo.

This script keeps the first external-user path short:

1. check the Python version;
2. create/install the local virtual environment unless told not to;
3. run the public-release review;
4. run the vault health check;
5. run the permissioned demo smoke test;
6. print the next files/commands to open.

It intentionally uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)


def _venv_python() -> Path:
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def _run(label: str, command: list[str]) -> None:
    print(f"\n==> {label}", flush=True)
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing command: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"{label} failed with exit code {exc.returncode}") from exc


def _check_python() -> None:
    current = sys.version_info[:2]
    print(f"Python: {sys.version.split()[0]}", flush=True)
    if current < MIN_PYTHON:
        needed = ".".join(map(str, MIN_PYTHON))
        actual = ".".join(map(str, current))
        raise SystemExit(f"Python {needed}+ is required; found {actual}")


def _ensure_venv(skip_install: bool) -> Path:
    if skip_install:
        return Path(sys.executable)

    python = _venv_python()
    if not python.exists():
        _run("Create local virtual environment", [sys.executable, "-m", "venv", ".venv"])

    _run(
        "Install Python dependencies",
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "-r",
            "requirements.txt",
        ],
    )
    return python


def _print_next_steps(python: Path, skip_install: bool) -> None:
    python_display = "python3" if skip_install else str(python.relative_to(ROOT))
    print(
        """

============================================================
SalesWiki first run completed.
============================================================

Open next:

1. README.md
2. docs/DEMO.en.md
3. demo/reports/dashboard-snapshots/sales-today.md
4. demo/reports/digests/my-day-ae.md

To ask the demo through an MCP client, generate ready-to-paste config:

  {python} scripts/generate_mcp_demo_config.py --personas ae,marketing,curator

To reset generated demo runtime state:

  rm -rf demo/mcp-demo demo/runtime
  {python} scripts/demo_dryrun.py --quiet

For Docker:

  docker compose run --rm first-run
""".format(python=python_display).strip(),
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and verify the public SalesWiki demo.")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="do not create .venv or install requirements; use the current Python",
    )
    parser.add_argument(
        "--full-tests",
        action="store_true",
        help="also run the full unittest suite after the demo smoke test",
    )
    args = parser.parse_args(argv)

    _check_python()
    python = _ensure_venv(args.skip_install)

    _run("Public release review", [str(python), "scripts/public_release_review.py"])
    _run("Vault health check", [str(python), "scripts/health_check.py"])
    _run("Permissioned demo smoke test", [str(python), "scripts/demo_dryrun.py", "--quiet"])
    if args.full_tests:
        _run("Full unit test suite", [str(python), "-m", "unittest", "discover", "-s", "tests"])

    _print_next_steps(python, args.skip_install)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
