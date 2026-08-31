#!/usr/bin/env python3
"""Create or verify a signed, externally stored audit-log checkpoint."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp.audit import AuditAnchorError, advance_anchor, create_anchor, verify_anchor  # noqa: E402


def _key(name: str) -> bytes:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing non-empty secret environment variable: {name}")
    return value.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify", "advance"))
    parser.add_argument("--audit", required=True, type=Path, help="Path to audit.jsonl")
    parser.add_argument("--anchor", required=True, type=Path, help="Path outside the audit runtime volume")
    parser.add_argument("--key-env", default="SALESWIKI_AUDIT_ANCHOR_KEY", help="Environment variable holding the signing key")
    args = parser.parse_args()
    key = _key(args.key_env)
    if args.action in ("create", "advance"):
        try:
            checkpoint = create_anchor(args.audit, args.anchor, key) if args.action == "create" else advance_anchor(args.audit, args.anchor, key)
        except AuditAnchorError as error:
            print(f"Audit anchor was not updated: {error}", file=sys.stderr)
            return 1
        print(f"Audit anchor {args.action}d: {checkpoint['count']} records protected.")
        return 0
    if verify_anchor(args.audit, args.anchor, key):
        print("Audit chain and signed checkpoint verify.")
        return 0
    print("Audit checkpoint verification failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
