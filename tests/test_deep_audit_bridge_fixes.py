"""Regression locks for bridge/gateway hardening fixes.

Covered areas: vault guard, chart zero-div, message split, relogin and autoplay
state isolation.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations" / "rocketchat"))

import bridge  # noqa: E402
import chartpng  # noqa: E402
import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import server, vault_guard  # noqa: E402


def _make_non_demo_vault() -> Path:
    """A vault whose single card carries no demo/synthetic marker (a stand-in for a
    production-shaped vault)."""
    root = Path(tempfile.mkdtemp(prefix="prod-vault-")) / "vault"
    card = root / "broad" / "wiki" / "entities" / "companies"
    card.mkdir(parents=True)
    (card / "Company - Real Co.md").write_text(
        "---\ntype: company\nentity_id: real-co\naccess: internal\n---\n\n## Live Intelligence\n- real\n",
        encoding="utf-8",
    )
    return root


class VaultGuard(unittest.TestCase):
    """Fixture / self-asserted-role surfaces must fail closed on a non-demo vault."""

    def test_is_demo_vault_true_for_generated_demo(self) -> None:
        vault = Path(tempfile.mkdtemp(prefix="demo-")) / "permissioned"
        gdv.generate_permissioned_demo(vault)
        self.assertTrue(vault_guard.is_demo_vault(vault))

    def test_is_demo_vault_false_for_unmarked_vault(self) -> None:
        self.assertFalse(vault_guard.is_demo_vault(_make_non_demo_vault()))

    def test_require_demo_vault_raises_on_non_demo(self) -> None:
        with self.assertRaises(RuntimeError):
            vault_guard.require_demo_vault(_make_non_demo_vault(), context="test")

    def test_override_env_allows_non_demo(self) -> None:
        with mock.patch.dict("os.environ", {vault_guard.ALLOW_PROD_ENV: "1"}):
            vault_guard.require_demo_vault(_make_non_demo_vault(), context="test")  # no raise

    def test_bridge_wiki_refuses_non_demo_vault(self) -> None:
        env = {"SALESWIKI_DEMO_VAULT": str(_make_non_demo_vault())}
        with mock.patch.dict("os.environ", env, clear=False):
            with self.assertRaises(RuntimeError):
                bridge.Wiki()

    def test_gateway_runtime_refuses_non_demo_vault(self) -> None:
        env = {
            "SALESWIKI_VAULT_ROOT": str(_make_non_demo_vault()),
            "SALESWIKI_DEMO_ACTOR": "demo-broad-viewer",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with self.assertRaises(RuntimeError):
                server.build_default_runtime()


class ChartZeroDivision(unittest.TestCase):
    """An all-zero deal list must not crash the pipeline chart."""

    def test_all_zero_values_do_not_raise(self) -> None:
        png = chartpng.pipeline_chart_png([("Atlas", 0, 0), ("Cedar", 0, 0)], "hos", "2026-07-03")
        self.assertTrue(png.startswith(b"\x89PNG"))


class MessageSplit(unittest.TestCase):
    """A single oversized code fence must still split under the limit."""

    def test_oversized_fence_is_split(self) -> None:
        text = "```\n" + ("x" * 10000) + "\n```"
        chunks = bridge.split_message(text, limit=4500)
        self.assertTrue(chunks)
        self.assertTrue(all(len(c) <= 4500 for c in chunks), "a chunk still exceeds the limit")

    def test_single_over_limit_line_is_sliced(self) -> None:
        chunks = bridge.split_message("y" * 9001, limit=4500)
        self.assertTrue(all(len(c) <= 4500 for c in chunks))


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):  # json.load calls .read()
        import json

        return json.dumps(self._payload).encode()


class ReloginOn401(unittest.TestCase):
    """An expired token must trigger one re-login + retry, not silent deafness."""

    def test_401_triggers_relogin_and_retry(self) -> None:
        rc = bridge.RocketChat("http://rc.example", "u", "p")
        rc.token, rc.user_id = "stale", "uid"
        state = {"n": 0}

        def fake_urlopen(req, timeout=30):
            url = req.full_url
            if "login" in url:
                return _Resp({"success": True, "data": {"authToken": "fresh", "userId": "uid2"}})
            state["n"] += 1
            if state["n"] == 1:
                raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))
            return _Resp({"success": True, "messages": [{"ts": "t1", "msg": "hi"}]})

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            msgs = rc.history("channels", "room", "1970-01-01T00:00:00.000Z")
        self.assertEqual([m["msg"] for m in msgs], ["hi"])
        self.assertEqual(rc.token, "fresh", "token was not refreshed on re-login")

    def test_post_warns_on_rejected_chunk(self) -> None:
        rc = bridge.RocketChat("http://rc.example", "u", "p")
        rc.token, rc.user_id = "t", "uid"
        rc._call = lambda path, data=None: {"success": False, "http": 400, "body": "too big"}
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            rc.post("room", "hello")
        self.assertIn("[warn]", err.getvalue())


class _FakeRC:
    def __init__(self) -> None:
        self.posts: list[str] = []

    def post(self, room_id: str, text: str) -> None:
        self.posts.append(text)

    def upload(self, *a, **k) -> dict:
        return {"success": True}


class ChildEnvHygiene(unittest.TestCase):
    """A spawned MCP-server/worker child must not inherit chat/model secrets."""

    def test_child_env_drops_secrets_keeps_overrides(self) -> None:
        secrets = {"RC_USER": "u", "RC_PASS": "p", "ANTHROPIC_API_KEY": "k",
                   "SALESWIKI_APPROVAL_KEY": "deadbeef"}
        with mock.patch.dict("os.environ", secrets, clear=False):
            env = bridge._child_env(SALESWIKI_VAULT_ROOT="/vault")
        self.assertNotIn("RC_PASS", env)
        self.assertNotIn("RC_USER", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual(env["SALESWIKI_VAULT_ROOT"], "/vault")
        self.assertEqual(env["SALESWIKI_APPROVAL_KEY"], "deadbeef", "the signing key must reach the child")


class AutoplayStateIsolation(unittest.TestCase):
    """Autoplay must not leave the live channel role mutated."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def test_autoplay_does_not_mutate_caller_state(self) -> None:
        state = {"role": "viewer", "company_name": "BluePeak Energy",
                 "company_id": "demo-company-bluepeak-energy"}
        saved = bridge.AUTOPLAY_SCRIPT
        bridge.AUTOPLAY_SCRIPT = [("switch role", "роль: curator")]
        try:
            bridge.run_autoplay(_FakeRC(), "room", self.wiki, state, 0)
        finally:
            bridge.AUTOPLAY_SCRIPT = saved
        self.assertEqual(state["role"], "viewer", "autoplay mutated the live channel role")


if __name__ == "__main__":
    unittest.main()
