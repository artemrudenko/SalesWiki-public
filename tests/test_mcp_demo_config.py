"""Tests for scripts/generate_mcp_demo_config.py (multi-persona MCP demo config).

Stdlib-only, no network and no `.venv` required: the module's functions are
imported directly and the venv lookup is patched where a config is emitted.
A tiny permissioned vault is generated into a temp dir where a real vault
layout is needed.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_demo_vault as gdv  # noqa: E402
import generate_mcp_demo_config as gmc  # noqa: E402

FAKE_PYTHON = Path("/fake/repo/.venv/bin/python")


def make_vault(base: Path) -> Path:
    """Generate a real (tiny, synthetic) permissioned vault for tests."""
    vault = base / "permissioned"
    gdv.generate_permissioned_demo(vault)
    return vault


class PersonaMappingTest(unittest.TestCase):
    def test_persona_aliases_map_to_expected_fixture_actors(self) -> None:
        expected = {
            "ae": "demo-ivan-ae",
            "marketing": "demo-nina-marketing",
            "curator": "demo-marina-curator",
            "hos": "demo-elena-hos",
            "revops": "demo-raj-revops",
            "admin": "demo-ada-admin",
            "legal": "demo-lena-legal",
            "sdr": "demo-sam-sdr",
            "sales": "demo-sam-sdr",
            "viewer": "demo-broad-viewer",
            "employee": "demo-broad-viewer",
        }
        for alias, actor_id in expected.items():
            self.assertEqual(gmc.PERSONA_ACTORS[alias], actor_id, alias)

    def test_all_mapped_actor_ids_are_valid_fixture_ids(self) -> None:
        schema = json.loads((ROOT / "schemas" / "identity-provider.json").read_text())
        fixture_ids = {u["id"] for u in schema["providers"]["fixture"]["users"]}
        for alias, actor_id in gmc.PERSONA_ACTORS.items():
            self.assertIn(actor_id, fixture_ids, f"persona {alias!r} maps to unknown actor")

    def test_parse_personas_splits_strips_and_dedupes(self) -> None:
        self.assertEqual(gmc.parse_personas("ae, marketing ,curator,ae"), ["ae", "marketing", "curator"])

    def test_unknown_persona_raises_clear_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            gmc.parse_personas("ae,wizard")
        message = str(ctx.exception)
        self.assertIn("wizard", message)
        self.assertIn("ae", message)  # error lists the known personas

    def test_empty_personas_raise(self) -> None:
        with self.assertRaises(ValueError):
            gmc.parse_personas(" , ")


class BuildConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mcp-demo-config-"))
        self.vault = make_vault(self.tmp)
        self.runtime = self.tmp / "runtime"
        self.config = gmc.build_mcp_config(
            personas=["ae", "marketing", "curator"],
            vault_root=self.vault,
            runtime_dir=self.runtime,
            python_exe=FAKE_PYTHON,
        )

    def test_one_server_entry_per_persona_named_by_role(self) -> None:
        self.assertEqual(
            sorted(self.config["mcpServers"]),
            ["saleswiki-ae", "saleswiki-curator", "saleswiki-marketing"],
        )

    def test_entry_shape_command_args_env(self) -> None:
        entry = self.config["mcpServers"]["saleswiki-ae"]
        self.assertEqual(entry["command"], str(FAKE_PYTHON))
        self.assertTrue(Path(entry["command"]).is_absolute())
        # server.py uses relative imports, so the real invocation is
        # `-m saleswiki_mcp.server` with PYTHONPATH at the repo root.
        self.assertEqual(entry["args"], ["-m", "saleswiki_mcp.server"])
        self.assertEqual(entry["env"]["PYTHONPATH"], str(gmc.ROOT))
        self.assertEqual(entry["env"]["SALESWIKI_DEMO_ACTOR"], "demo-ivan-ae")

    def test_entries_share_one_vault_and_one_runtime(self) -> None:
        vaults = {e["env"]["SALESWIKI_VAULT_ROOT"] for e in self.config["mcpServers"].values()}
        runtimes = {e["env"]["SALESWIKI_RUNTIME_DIR"] for e in self.config["mcpServers"].values()}
        self.assertEqual(vaults, {str(self.vault.resolve())})
        self.assertEqual(runtimes, {str(self.runtime.resolve())})
        self.assertTrue(Path(vaults.pop()).is_absolute())

    def test_actor_env_matches_persona(self) -> None:
        actors = {
            name: entry["env"]["SALESWIKI_DEMO_ACTOR"]
            for name, entry in self.config["mcpServers"].items()
        }
        self.assertEqual(
            actors,
            {
                "saleswiki-ae": "demo-ivan-ae",
                "saleswiki-marketing": "demo-nina-marketing",
                "saleswiki-curator": "demo-marina-curator",
            },
        )


class VaultValidationTest(unittest.TestCase):
    def test_generated_vault_passes_validation(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="mcp-demo-vault-"))
        vault = make_vault(tmp)
        gmc.validate_vault(vault)  # must not raise

    def test_non_permissioned_dir_is_rejected(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="mcp-demo-bad-vault-"))
        (tmp / "notes").mkdir()
        with self.assertRaises(ValueError) as ctx:
            gmc.validate_vault(tmp)
        self.assertIn("broad", str(ctx.exception))  # names the missing boundary folders

    def test_missing_dir_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gmc.validate_vault(Path("/nonexistent/mcp-demo-vault"))


class MainCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mcp-demo-cli-"))
        self.vault = make_vault(self.tmp)

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with mock.patch.object(gmc, "find_venv_python", return_value=FAKE_PYTHON), \
                mock.patch.object(sys, "stdout", stdout), \
                mock.patch.object(sys, "stderr", stderr):
            code = gmc.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_out_writes_valid_json_file(self) -> None:
        out = self.tmp / "mcp.json"
        code, _, _ = self.run_main(
            ["--personas", "ae,marketing,curator", "--vault", str(self.vault), "--out", str(out)]
        )
        self.assertEqual(code, 0)
        written = json.loads(out.read_text())
        self.assertEqual(len(written["mcpServers"]), 3)
        self.assertIn("saleswiki-curator", written["mcpServers"])

    def test_stdout_mode_prints_valid_json(self) -> None:
        code, stdout, stderr = self.run_main(["--personas", "ae", "--vault", str(self.vault)])
        self.assertEqual(code, 0)
        parsed = json.loads(stdout)
        self.assertIn("saleswiki-ae", parsed["mcpServers"])
        self.assertIn("mcpServers", stderr)  # paste hint goes to stderr, not stdout

    def test_unknown_persona_exits_nonzero(self) -> None:
        code, _, stderr = self.run_main(["--personas", "ae,wizard", "--vault", str(self.vault)])
        self.assertNotEqual(code, 0)
        self.assertIn("wizard", stderr)

    def test_bad_vault_exits_nonzero(self) -> None:
        bad = self.tmp / "empty"
        bad.mkdir()
        code, _, stderr = self.run_main(["--personas", "ae", "--vault", str(bad)])
        self.assertNotEqual(code, 0)
        self.assertIn("permissioned", stderr)

    def test_missing_venv_exits_nonzero_with_install_hint(self) -> None:
        stdout, stderr = StringIO(), StringIO()
        with mock.patch.object(gmc, "find_venv_python", return_value=None), \
                mock.patch.object(sys, "stdout", stdout), \
                mock.patch.object(sys, "stderr", stderr):
            code = gmc.main(["--personas", "ae", "--vault", str(self.vault)])
        self.assertNotEqual(code, 0)
        self.assertIn("python3 -m venv .venv && .venv/bin/pip install -r requirements.txt", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
