#!/usr/bin/env python3
"""Heuristic public-release review for SalesWiki.

The goal is to catch mistakes before publishing the repository: missing release
metadata, tracked credentials, real-looking local service URLs in examples, and
tracked private runtime artifacts. Ignored local tool state is allowed because it
is neither committed nor copied into the Docker image. The review is intentionally conservative and uses only
the Python standard library.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    ".dockerignore",
    "Dockerfile",
    "docker-compose.yml",
    "docs/DEPLOYMENT.en.md",
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"BEGIN (?:RSA|OPENSSH|DSA|EC|PRIVATE) KEY")),
    ("bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I)),
    ("api key assignment", re.compile(r"\b(?:api[_-]?key|client_secret|secret|password|passwd|token)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{16,}", re.I)),
    ("committed env var", re.compile(r"\b(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|OPENROUTER_API_KEY|HUBSPOT_API_KEY|RC_PASS)\s*=\s*['\"]?[^'\"\s]+", re.I)),
    ("real Rocket.Chat URL assignment", re.compile(r"\bRC_URL\s*=\s*['\"]?https?://(?!your-|[^'\"\s]*example\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)),
)

ALLOWLIST_PATTERNS = (
    re.compile(r"your-[A-Za-z0-9_.-]+"),
    re.compile(r"example\.com"),
    re.compile(r"example\.invalid"),
    re.compile(r"demo\.invalid"),
    re.compile(r"test-key"),
    re.compile(r"LEAK-CANARY"),
)

SKIP_PARTS = {
    ".git",
    ".venv",
    ".gstack",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    ".remember",
    ".obsidian",
}

SKIP_SUFFIXES = {
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".tar",
    ".gz",
    ".zip",
}

TRACKED_FORBIDDEN_PATHS = (
    ".env",
    ".claude/settings.local.json",
    ".gstack",
    ".remember",
    "RESUME.md",
)


def _candidate_files() -> list[Path]:
    """Return git-tracked files when git metadata exists; otherwise scan the
    materialized working tree (Docker images intentionally exclude `.git`)."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return sorted(path for path in ROOT.rglob("*") if path.is_file())
    return [ROOT / line for line in proc.stdout.splitlines() if line.strip()]


def _is_skipped(path: Path) -> bool:
    rel_parts = set(path.relative_to(ROOT).parts)
    return bool(rel_parts & SKIP_PARTS) or path.suffix.lower() in SKIP_SUFFIXES


def _looks_allowlisted(line: str) -> bool:
    return any(pattern.search(line) for pattern in ALLOWLIST_PATTERNS)


def _history_secret_findings() -> list[str]:
    """Scan every reachable historical blob without printing any candidate secret.

    `git grep` over commit diffs would echo the matching value into CI logs.  We
    deliberately report only a short commit id, path and heuristic label.
    """
    try:
        commits = subprocess.run(
            ["git", "rev-list", "--all"], cwd=ROOT, check=True, text=True,
            capture_output=True,
        ).stdout.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    findings: list[str] = []
    seen_blobs: set[str] = set()
    for commit in commits:
        tree = subprocess.run(
            ["git", "ls-tree", "-r", "-z", "--full-tree", commit], cwd=ROOT,
            check=True, capture_output=True,
        ).stdout
        for record in tree.split(b"\0"):
            try:
                metadata, raw_path = record.split(b"\t", 1)
                _mode, object_type, blob_id = metadata.decode("ascii").split(" ", 2)
            except ValueError:
                continue
            if object_type != "blob" or blob_id in seen_blobs:
                continue
            seen_blobs.add(blob_id)
            blob = subprocess.run(
                ["git", "cat-file", "blob", blob_id], cwd=ROOT, capture_output=True,
            ).stdout
            if len(blob) > 1_000_000:
                continue
            try:
                text = blob.decode("utf-8")
                path = raw_path.decode("utf-8", "replace")
            except UnicodeDecodeError:
                continue
            for line in text.splitlines():
                if _looks_allowlisted(line):
                    continue
                for label, pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append(f"history {commit[:12]}:{path}: possible {label}")
                        break
    return findings


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required public-release file: {rel}")

    tracked = _candidate_files()
    tracked_rel = {str(path.relative_to(ROOT)) for path in tracked}
    for forbidden in TRACKED_FORBIDDEN_PATHS:
        if forbidden in tracked_rel or any(item.startswith(forbidden.rstrip("/") + "/") for item in tracked_rel):
            errors.append(f"tracked local/private file: {forbidden}")
    for path in tracked:
        if _is_skipped(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _looks_allowlisted(line):
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    errors.append(f"{path.relative_to(ROOT)}:{lineno}: possible {label}")

    errors.extend(_history_secret_findings())

    print("SalesWiki public release review")
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
