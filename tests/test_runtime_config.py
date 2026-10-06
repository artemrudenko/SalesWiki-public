"""Runtime configuration contracts and secret-safety tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from saleswiki_runtime.config import ConfigError, load_runtime_settings, parse_runtime_settings
from saleswiki_runtime.__main__ import _doctor


ROOT = Path(__file__).resolve().parents[1]


def write_config(root: Path, body: str) -> Path:
    path = root / "runtime.toml"
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return path


class RuntimeConfig(unittest.TestCase):
    def test_example_config_is_valid_and_resolves_paths_from_file(self) -> None:
        settings = parse_runtime_settings(ROOT / "config" / "runtime.example.toml")
        self.assertEqual(settings.profile, "demo")
        self.assertEqual(settings.vault.root, ROOT / "demo" / "permissioned")
        adapter = settings.enabled_adapter("rocketchat")
        self.assertEqual(adapter.conversation, "saleswiki-demo")
        self.assertEqual(adapter.endpoint_env, "ROCKETCHAT_URL")
        self.assertFalse(settings.workbench.enabled)
        self.assertEqual(settings.workbench.host, "127.0.0.1")
        self.assertEqual(settings.workbench.port, 8787)
        self.assertEqual(settings.workbench.timeout_seconds, 15.0)
        self.assertEqual(settings.workbench.max_concurrent_requests, 4)

    def test_workbench_demo_example_is_ready_for_the_local_bff(self) -> None:
        settings = parse_runtime_settings(ROOT / "config" / "workbench-demo.example.toml")
        self.assertTrue(settings.workbench.enabled)
        self.assertEqual(settings.workbench.identity_provider, "fixture")
        self.assertEqual(settings.workbench.mcp_transport, "stdio")
        self.assertTrue(settings.workbench.allow_fixture_persona_switching)
        self.assertEqual(settings.vault.root, ROOT / "demo" / "permissioned")
        self.assertEqual(settings.vault.runtime, ROOT / ".runtime" / "workbench")
        with mock.patch.dict(os.environ, {"SALESWIKI_DEMO_ACTOR": "demo-ethan-ae"}, clear=False):
            passed, failed = _doctor(settings)
        self.assertEqual(failed, [])
        self.assertTrue(any("Workbench fixture actor resolves" in item for item in passed))

    def test_invalid_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_config(Path(tmp), "version = 2\nprofile = \"demo\"")
            with self.assertRaisesRegex(ConfigError, "version"):
                parse_runtime_settings(path)

    def test_fixture_identity_is_rejected_outside_demo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_config(
                Path(tmp),
                """
                version = 1
                profile = "production"
                [chat.adapters.chat]
                provider = "rocketchat"
                enabled = true
                identity_provider = "fixture"
                conversation = "sales"
                url_env = "RC_URL"
                user_env = "RC_USER"
                password_env = "RC_PASS"
                """,
            )
            with self.assertRaisesRegex(ConfigError, "fixture identity"):
                parse_runtime_settings(path)

    def test_fixture_workbench_is_rejected_outside_demo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_config(
                Path(tmp),
                """
                version = 1
                profile = "production"
                [workbench]
                enabled = true
                identity_provider = "fixture"
                """,
            )
            with self.assertRaisesRegex(ConfigError, "fixture Workbench identity"):
                parse_runtime_settings(path)

    def test_workbench_port_and_transport_are_typed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_port = write_config(
                Path(tmp),
                "version = 1\nprofile = \"demo\"\n[workbench]\nport = 70000",
            )
            with self.assertRaisesRegex(ConfigError, "workbench.port"):
                parse_runtime_settings(bad_port)
            bad_transport = write_config(
                Path(tmp),
                "version = 1\nprofile = \"demo\"\n[workbench]\nmcp_transport = \"browser\"",
            )
            with self.assertRaisesRegex(ConfigError, "mcp_transport"):
                parse_runtime_settings(bad_transport)

    def test_workbench_limits_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_timeout = write_config(
                Path(tmp),
                "version = 1\nprofile = \"demo\"\n[workbench]\ntimeout_seconds = 60",
            )
            with self.assertRaisesRegex(ConfigError, "timeout_seconds"):
                parse_runtime_settings(bad_timeout)
            bad_concurrency = write_config(
                Path(tmp),
                "version = 1\nprofile = \"demo\"\n[workbench]\nmax_concurrent_requests = 0",
            )
            with self.assertRaisesRegex(ConfigError, "max_concurrent_requests"):
                parse_runtime_settings(bad_concurrency)

    def test_fixture_persona_switching_is_demo_only_and_typed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid_type = write_config(Path(tmp), "version = 1\nprofile = \"demo\"\n[workbench]\nallow_fixture_persona_switching = \"yes\"")
            with self.assertRaisesRegex(ConfigError, "allow_fixture_persona_switching"):
                parse_runtime_settings(invalid_type)
            production = write_config(Path(tmp), "version = 1\nprofile = \"production\"\n[workbench]\nidentity_provider = \"oidc\"\nallow_fixture_persona_switching = true")
            with self.assertRaisesRegex(ConfigError, "fixture persona switching"):
                parse_runtime_settings(production)

    def test_secret_reference_must_be_an_environment_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_config(
                Path(tmp),
                """
                version = 1
                profile = "demo"
                [chat.adapters.chat]
                provider = "rocketchat"
                enabled = true
                conversation = "sales"
                url_env = "https://chat.example.com"
                user_env = "RC_USER"
                password_env = "RC_PASS"
                """,
            )
            with self.assertRaisesRegex(ConfigError, "environment variable"):
                parse_runtime_settings(path)

    def test_redacted_output_never_contains_secret_values(self) -> None:
        settings = parse_runtime_settings(ROOT / "config" / "runtime.example.toml")
        env = {
            "ROCKETCHAT_URL": "https://private-chat.example.invalid",
            "ROCKETCHAT_USER": "private-user",
            "ROCKETCHAT_PASSWORD": "very-private-password",
        }
        rendered = json.dumps(settings.redacted(env))
        self.assertNotIn("very-private-password", rendered)
        self.assertNotIn("private-user", rendered)
        self.assertNotIn("private-chat.example", rendered)
        self.assertIn('"present": true', rendered)

    def test_legacy_environment_maps_to_typed_settings(self) -> None:
        env = {
            "RC_URL": "https://chat.example.invalid",
            "RC_USER": "bot",
            "RC_PASS": "password",
            "RC_CHANNEL": "sales",
            "RC_TRIGGER": "!",
            "RC_POLL": "3",
            "RC_USE_MCP": "1",
        }
        with mock.patch("builtins.print") as warning:
            settings = load_runtime_settings(env=env)
        warning.assert_called_once()
        adapter = settings.enabled_adapter("rocketchat")
        self.assertEqual(adapter.trigger, "!")
        self.assertEqual(adapter.poll_seconds, 3.0)
        self.assertTrue(settings.features.use_mcp)

    def test_legacy_environment_rejects_ambiguous_target(self) -> None:
        env = {
            "RC_URL": "https://chat.example.invalid",
            "RC_USER": "bot",
            "RC_PASS": "password",
            "RC_CHANNEL": "sales",
            "RC_DM": "bot",
        }
        with self.assertRaisesRegex(ConfigError, "exactly one"):
            load_runtime_settings(env=env)

    def test_cli_show_requires_redacted_flag(self) -> None:
        env = {**os.environ, "SALESWIKI_CONFIG": str(ROOT / "config" / "runtime.example.toml")}
        proc = subprocess.run(
            [sys.executable, "-m", "saleswiki_runtime", "config", "show"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Refusing unredacted", proc.stderr)

    def test_cli_validate_example(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "saleswiki_runtime",
                "--config",
                str(ROOT / "config" / "runtime.example.toml"),
                "config",
                "validate",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK: runtime config is valid", proc.stdout)


if __name__ == "__main__":
    unittest.main()
