"""Contract tests for permissioned-knowledge Slice 1 schemas.

These validate the three machine-readable contracts that the gateway and
worker depend on: access policy, boundary registry and identity provider.
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def load(rel: str) -> dict:
    return json.loads((SCHEMAS / rel).read_text(encoding="utf-8"))


class BoundaryRegistryContract(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = load("boundary-registry.json")

    def test_has_boundaries_and_default(self) -> None:
        self.assertIn("boundaries", self.reg)
        self.assertTrue(self.reg["boundaries"], "boundaries must be non-empty")
        self.assertIn("default_boundary", self.reg)

    def test_default_boundary_is_defined(self) -> None:
        ids = {b["id"] for b in self.reg["boundaries"]}
        self.assertIn(self.reg["default_boundary"], ids)

    def test_path_map_references_defined_boundaries(self) -> None:
        ids = {b["id"] for b in self.reg["boundaries"]}
        for entry in self.reg.get("path_map", []):
            self.assertIn("prefix", entry)
            self.assertIn(entry["boundary"], ids)

    def test_slice_boundaries_present(self) -> None:
        ids = {b["id"] for b in self.reg["boundaries"]}
        for required in ("broad", "sales-confidential", "personal-data"):
            self.assertIn(required, ids)


class AccessPolicyContract(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load("access-policy.json")
        self.registry = load("boundary-registry.json")

    def test_has_roles_and_operations(self) -> None:
        self.assertTrue(self.policy.get("roles"), "roles must be non-empty")
        self.assertTrue(self.policy.get("operations"), "operations must be non-empty")

    def test_role_boundaries_are_defined(self) -> None:
        boundary_ids = {b["id"] for b in self.registry["boundaries"]}
        for role in self.policy["roles"]:
            self.assertIn("id", role)
            for boundary in role.get("boundaries", []):
                self.assertIn(boundary, boundary_ids, f"role {role['id']} references unknown boundary {boundary}")

    def test_slice_roles_present(self) -> None:
        ids = {r["id"] for r in self.policy["roles"]}
        for required in ("employee-viewer", "sales-owner", "marketing"):
            self.assertIn(required, ids)

    def test_marketing_cannot_read_sales_confidential(self) -> None:
        marketing = next(r for r in self.policy["roles"] if r["id"] == "marketing")
        self.assertNotIn("sales-confidential", marketing.get("boundaries", []))

    def test_personal_data_default_deny(self) -> None:
        self.assertEqual(self.policy.get("rules", {}).get("personal_data_default"), "deny")


class IdentityProviderContract(unittest.TestCase):
    def setUp(self) -> None:
        self.idp = load("identity-provider.json")
        self.policy = load("access-policy.json")

    def test_active_provider_is_defined(self) -> None:
        self.assertIn("active_provider", self.idp)
        self.assertIn(self.idp["active_provider"], self.idp.get("providers", {}))

    def test_fixture_users_reference_defined_roles(self) -> None:
        role_ids = {r["id"] for r in self.policy["roles"]}
        fixture = self.idp["providers"]["fixture"]
        self.assertTrue(fixture.get("users"), "fixture provider needs demo users")
        for user in fixture["users"]:
            self.assertIn("id", user)
            self.assertIn(user["role"], role_ids, f"user {user['id']} has unknown role {user['role']}")

    def test_google_group_map_references_defined_roles(self) -> None:
        role_ids = {r["id"] for r in self.policy["roles"]}
        google = self.idp["providers"].get("google-oidc", {})
        for group, role in google.get("group_role_map", {}).items():
            self.assertIn(role, role_ids, f"google group {group} maps to unknown role {role}")

    def test_no_real_secret_in_repo(self) -> None:
        google = self.idp["providers"].get("google-oidc", {})
        client_id = google.get("client_id", "")
        # Placeholder only; a real client id must never be committed.
        self.assertTrue(
            client_id == "" or client_id.startswith("REPLACE") or client_id.endswith(".apps.googleusercontent.com") is False,
            "identity-provider.json must not contain a real Google client secret/id",
        )


if __name__ == "__main__":
    unittest.main()
