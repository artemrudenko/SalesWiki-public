"""RocketChat REST client coverage (review H3).

The network/IO surface (login, room/DM resolution, history, post, delete, the
_call transport and upload) was almost untested — yet it is the newest,
side-effecting code, and a regression in login or room-resolution silently
breaks the whole demo. These tests inject a fake `_call` for the high-level
methods and patch urlopen for the transport, covering success, the RuntimeError
paths and the HTTPError branch — without any real network.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations" / "rocketchat"))
sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402


def rc() -> "bridge.RocketChat":
    return bridge.RocketChat("https://chat.example/", "bot", "pw")


class _FakeResp(io.BytesIO):
    """Minimal urlopen() return: a context manager yielding JSON bytes."""

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *exc) -> bool:
        return False


def _http_error(code: int = 403, body: bytes = b"blocked by WAF") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://chat.example", code, "Forbidden", {}, io.BytesIO(body))


class LoginAndResolve(unittest.TestCase):
    def test_login_success_sets_credentials(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {
            "success": True, "data": {"authToken": "tok", "userId": "uid"}
        }
        client.login()
        self.assertEqual((client.token, client.user_id), ("tok", "uid"))

    def test_login_failure_raises(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {"success": False, "error": "bad creds"}
        with self.assertRaises(RuntimeError):
            client.login()

    def test_resolve_room_public_then_private(self) -> None:
        client = rc()
        client._call = lambda path, data=None: (
            {"success": True, "channel": {"_id": "C1"}} if "channels.info" in path
            else {"success": False}
        )
        self.assertEqual(client.resolve_room("demo"), ("C1", "channels"))

        def private_only(path, data=None):
            if "channels.info" in path:
                return {"success": False}
            return {"success": True, "group": {"_id": "G1"}}

        client._call = private_only
        self.assertEqual(client.resolve_room("demo"), ("G1", "groups"))

    def test_resolve_room_not_found_raises(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {"success": False}
        with self.assertRaises(RuntimeError):
            client.resolve_room("ghost")

    def test_resolve_dm_success_and_failure(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {"success": True, "room": {"_id": "D1"}}
        self.assertEqual(client.resolve_dm("me"), ("D1", "im"))
        client._call = lambda path, data=None: {"success": False}
        with self.assertRaises(RuntimeError):
            client.resolve_dm("me")


class HistoryPostDelete(unittest.TestCase):
    def test_history_sorts_ascending(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {
            "success": True,
            "messages": [{"ts": "2026-02", "_id": "b"}, {"ts": "2026-01", "_id": "a"}],
        }
        out = client.history("channels", "R1", "")
        self.assertEqual([m["_id"] for m in out], ["a", "b"])

    def test_history_failure_returns_empty(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {"success": False}
        self.assertEqual(client.history("channels", "R1", ""), [])

    def test_post_sends_payload(self) -> None:
        client = rc()
        seen = {}

        def capture(path, data=None):
            seen["path"], seen["data"] = path, data
            return {"success": True}

        client._call = capture
        client.post("R1", "hello")
        self.assertIn("chat.postMessage", seen["path"])
        self.assertEqual(seen["data"], {"roomId": "R1", "text": "hello"})

    def test_delete_message_returns_result(self) -> None:
        client = rc()
        client._call = lambda path, data=None: {"success": True}
        self.assertTrue(client.delete_message("R1", "M1")["success"])

    def test_clear_history_counts_deleted_and_skipped(self) -> None:
        client = rc()
        client._all_message_ids = lambda kind, room_id: ["m1", "m2", "m3"]
        # m2 is undeletable (someone else's message).
        client.delete_message = lambda room_id, mid: {"success": mid != "m2"}
        self.assertEqual(client.clear_history("im", "R1"), (2, 1))


class CallTransport(unittest.TestCase):
    def test_call_parses_json_response(self) -> None:
        client = rc()
        with mock.patch("bridge.urllib.request.urlopen",
                        return_value=_FakeResp(json.dumps({"success": True, "n": 1}).encode())):
            out = client._call("/api/v1/anything")
        self.assertEqual(out, {"success": True, "n": 1})

    def test_call_httperror_returns_failure_dict(self) -> None:
        client = rc()
        with mock.patch("bridge.urllib.request.urlopen", side_effect=_http_error(403)):
            out = client._call("/api/v1/anything")
        self.assertFalse(out["success"])
        self.assertEqual(out["http"], 403)

    def test_upload_uses_the_modern_media_flow(self) -> None:
        # Rocket.Chat 7 removed rooms.upload: the client must POST the file to
        # rooms.media and then confirm it (with the caption) via mediaConfirm.
        client = rc()
        client.token, client.user_id = "tok", "uid"
        urls: list[str] = []

        def fake(req, timeout=0):
            urls.append(req.full_url)
            if "rooms.media/" in req.full_url:
                return _FakeResp(json.dumps({"success": True, "file": {"_id": "F1"}}).encode())
            return _FakeResp(json.dumps({"success": True}).encode())

        with mock.patch("bridge.urllib.request.urlopen", side_effect=fake):
            out = client.upload("R1", "f.png", b"\x89PNG", "image/png", caption="hi")
        self.assertTrue(out["success"])
        self.assertIn("rooms.media/R1", urls[0])
        self.assertIn("rooms.mediaConfirm/R1/F1", urls[1])

    def test_upload_falls_back_to_legacy_endpoint_on_404(self) -> None:
        client = rc()
        client.token, client.user_id = "tok", "uid"
        urls: list[str] = []

        def fake(req, timeout=0):
            urls.append(req.full_url)
            if "rooms.media/" in req.full_url:
                raise _http_error(404, b"unknown endpoint")
            return _FakeResp(json.dumps({"success": True}).encode())

        with mock.patch("bridge.urllib.request.urlopen", side_effect=fake):
            out = client.upload("R1", "f.csv", b"data", "text/csv")
        self.assertTrue(out["success"])
        self.assertIn("rooms.upload/R1", urls[1])

    def test_upload_httperror_returns_failure_dict(self) -> None:
        client = rc()
        client.token, client.user_id = "tok", "uid"
        with mock.patch("bridge.urllib.request.urlopen", side_effect=_http_error(500)):
            out = client.upload("R1", "f.csv", b"data", "text/csv")
        self.assertFalse(out["success"])
        self.assertEqual(out["http"], 500)


if __name__ == "__main__":
    unittest.main()


class LongMessageSplit(unittest.TestCase):
    """Rocket.Chat rejects messages over ~5k chars (error-message-size-exceeded),
    which silently ate the grown `демо` cheat-sheet. post() must split long
    texts on line boundaries without ever breaking a ``` code fence."""

    def test_short_text_is_one_chunk(self) -> None:
        self.assertEqual(bridge.split_message("hi", limit=100), ["hi"])

    def test_chunks_respect_limit_and_fences_and_rejoin(self) -> None:
        block = "```\n" + "\n".join(f"row {i}" for i in range(30)) + "\n```"
        prose = "\n".join(f"para line {i}" for i in range(80))
        text = "\n\n".join([block, prose, block, prose])
        chunks = bridge.split_message(text, limit=800)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("\n".join(chunks), text)  # nothing lost
        for ch in chunks:
            self.assertLessEqual(len(ch), 800)
            self.assertEqual(ch.count("```") % 2, 0, "fence broken across chunks")

    def test_demo_cheatsheet_fits_after_split(self) -> None:
        chunks = bridge.split_message(bridge.demo_help(), limit=4500)
        self.assertGreater(len(chunks), 1)
        for ch in chunks:
            self.assertLessEqual(len(ch), 4500)

    def test_post_sends_every_chunk(self) -> None:
        client = rc()
        sent: list[str] = []

        def capture(path, data=None):
            sent.append(data["text"])
            return {"success": True}

        client._call = capture
        client.post("R1", "line\n" * 3000)  # ~15k chars
        self.assertGreater(len(sent), 2)
