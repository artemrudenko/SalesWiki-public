"""Tests for scripts/refresh.py - one-command vault refresh."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFRESH = PROJECT_ROOT / "scripts" / "refresh.py"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import refresh  # noqa: E402


class TestBuildSteps(unittest.TestCase):
    def test_production_steps_use_default_roots(self) -> None:
        steps = refresh.build_steps("production")
        self.assertEqual(len(steps), 3)
        self.assertIn("health_check.py", steps[0].command[1])
        self.assertIn("build_indexes.py", steps[1].command[1])
        self.assertNotIn("--no-update-state", steps[1].command)
        self.assertIn("build_dashboard_snapshots.py", steps[2].command[1])

    def test_demo_steps_target_demo_roots_and_skip_state(self) -> None:
        steps = refresh.build_steps("demo")
        self.assertEqual(len(steps), 3)
        index_cmd = steps[1].command
        self.assertIn("--no-update-state", index_cmd)
        self.assertIn(str(PROJECT_ROOT / "demo" / "demo-vault"), index_cmd)
        self.assertIn(str(PROJECT_ROOT / "demo" / "indexes"), index_cmd)
        snapshot_cmd = steps[2].command
        self.assertIn(str(PROJECT_ROOT / "demo" / "indexes"), snapshot_cmd)
        self.assertIn(
            str(PROJECT_ROOT / "demo" / "reports" / "dashboard-snapshots"),
            snapshot_cmd,
        )
        # Snapshot links must rebase to the demo vault, not the snapshot dir.
        self.assertIn("--vault-root", snapshot_cmd)
        self.assertIn(str(PROJECT_ROOT / "demo" / "demo-vault"), snapshot_cmd)

    def test_unknown_contour_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            refresh.build_steps("staging")


class TestCli(unittest.TestCase):
    def run_refresh(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REFRESH), *args],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

    def test_dry_run_lists_steps_without_executing(self) -> None:
        result = self.run_refresh("--demo", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("health_check.py", result.stdout)
        self.assertIn("build_indexes.py", result.stdout)
        self.assertIn("build_dashboard_snapshots.py", result.stdout)

    def test_demo_build_pipeline_runs_end_to_end_without_side_effects(self) -> None:
        # Exercise the same demo build the demo contour runs (indexes ->
        # snapshots, including link rebasing) but entirely inside a temp dir, so
        # the pre-flight test suite never rewrites tracked demo artifacts.
        import re
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory(prefix="refresh-demo-") as tmp:
            tmp_root = Path(tmp)
            vault = tmp_root / "demo-vault"
            indexes = tmp_root / "indexes"
            output = tmp_root / "reports" / "dashboard-snapshots"
            shutil.copytree(PROJECT_ROOT / "demo" / "demo-vault", vault)

            build_indexes = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "scripts" / "build_indexes.py"),
                    "--source-root", str(vault),
                    "--output-root", str(indexes),
                    "--no-update-state",
                ],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            self.assertEqual(build_indexes.returncode, 0, build_indexes.stderr)

            build_snapshots = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "scripts" / "build_dashboard_snapshots.py"),
                    "--index-root", str(indexes),
                    "--output-root", str(output),
                    "--vault-root", str(vault),
                ],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            self.assertEqual(build_snapshots.returncode, 0, build_snapshots.stderr)

            snapshot = output / "sales-today.md"
            self.assertTrue(snapshot.exists())
            text = snapshot.read_text(encoding="utf-8")
            self.assertIn("| [", text)
            # The first card link must resolve to a real card in the demo vault.
            target = re.search(r"\[[^\]]+\]\(([^)]+)\)", text).group(1)
            self.assertTrue((output / target).resolve().exists(), f"dangling link: {target}")


if __name__ == "__main__":
    unittest.main()
