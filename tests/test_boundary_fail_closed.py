"""Fail-closed default boundary (security review H1).

A card whose path matches no explicit path_map prefix (a root-level file, a
typo'd folder, a future `partners/`/`legal-review/` tree, or an importer that
drops files at the vault root) must NOT silently become world-readable `broad`.
The default boundary must be one that no role can read, so a misfiled sensitive
card fails closed and is surfaced (by the health check) rather than leaked.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from saleswiki_mcp.boundaries import resolve_boundary

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def load(rel: str) -> dict:
    return json.loads((SCHEMAS / rel).read_text(encoding="utf-8"))


class DefaultBoundaryFailClosed(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = load("boundary-registry.json")
        self.policy = load("access-policy.json")

    def test_unmapped_path_does_not_resolve_to_broad(self) -> None:
        """Any path outside the known prefixes must not be treated as broad."""
        for rel in (
            "partners/Deal - Secret Co.md",
            "Company - Root Level.md",
            "sales-confidential 2/Deal - Misfiled.md",  # macOS-style dup folder
            "legal-review/Memo.md",
        ):
            self.assertNotEqual(
                resolve_boundary(rel, self.reg),
                "broad",
                f"{rel} fell through to world-readable broad",
            )

    def test_default_boundary_is_readable_by_no_role(self) -> None:
        """The fallback boundary must be in no role's readable boundary set."""
        default = self.reg["default_boundary"]
        for role in self.policy["roles"]:
            self.assertNotIn(
                default,
                role.get("boundaries", []),
                f"role {role['id']} can read the fail-closed default boundary {default!r}",
            )

    def test_missing_default_key_falls_back_closed(self) -> None:
        """A registry with no default_boundary must still fail closed, never broad."""
        reg = {"path_map": []}
        self.assertNotEqual(resolve_boundary("anything.md", reg), "broad")

    def test_known_prefixes_still_map_correctly(self) -> None:
        """Regression: explicit prefixes keep resolving to their boundary."""
        self.assertEqual(resolve_boundary("broad/wiki/x.md", self.reg), "broad")
        self.assertEqual(
            resolve_boundary("sales-confidential/wiki/x.md", self.reg),
            "sales-confidential",
        )
        self.assertEqual(
            resolve_boundary("personal-data/refs/x.md", self.reg),
            "personal-data",
        )


if __name__ == "__main__":
    unittest.main()
