#!/usr/bin/env python3
"""Create a history-free public release snapshot from the current Git commit.

The private working repository remains the source of truth. This helper exports
only files tracked at ``HEAD`` after the public-release gate has passed; it does
not copy ``.git`` or ignored local state. Initialise a separate public GitHub
repository in the resulting directory and make a fresh commit there.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# The private source repository also holds working social copy. It is useful to
# keep that copy versioned alongside the product work, but it is not part of the
# public developer repository. Keep this list explicit so a new export cannot
# accidentally publish it just because it is tracked on the source branch.
PRIVATE_EDITORIAL_PATHS = (
    Path("docs/publications/PRIVATE_LINKEDIN.md"),
    Path("docs/publications/linkedin-launch-post.md"),
    Path("docs/publications/linkedin-01-what-ai-sales-answer-should-prove.md"),
)


def run_bytes(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True)


def remove_private_editorial(output: Path) -> None:
    """Remove intentionally private publication drafts from a public snapshot."""
    for relative_path in PRIVATE_EDITORIAL_PATHS:
        candidate = output / relative_path
        if candidate.is_file():
            candidate.unlink()
        elif candidate.exists():
            raise RuntimeError(f"Expected a file at {relative_path}, found another path type")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a checked, history-free public SalesWiki snapshot")
    parser.add_argument("--output", required=True, type=Path, help="new empty destination directory")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()

    if output.exists() and any(output.iterdir()):
        parser.error("--output must be a new or empty directory; refusing to overwrite files")

    review = subprocess.run([sys.executable, "scripts/public_release_review.py"], cwd=ROOT)
    if review.returncode:
        return review.returncode

    try:
        archive = run_bytes(["git", "archive", "--format=tar", "HEAD"])
    except subprocess.CalledProcessError as error:
        print(error.stderr.decode("utf-8", "replace"), file=sys.stderr)
        return error.returncode

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as handle:
        archive_path = Path(handle.name)
        archive_path.write_bytes(archive.stdout)
    try:
        with tarfile.open(archive_path) as tar:
            tar.extractall(output, filter="data")
    finally:
        archive_path.unlink(missing_ok=True)

    remove_private_editorial(output)

    print(f"Public snapshot exported to {output}")
    print("Next: inspect it, run its checks, then initialise the separate public Git repository there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
