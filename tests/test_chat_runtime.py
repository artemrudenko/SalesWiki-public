"""Provider-neutral chat runtime contract tests."""

from __future__ import annotations

import unittest

from integrations.chat.models import (
    ChatCapabilities,
    ClearConversation,
    FileResponse,
    InboundBatch,
    InboundMessage,
    StartDemo,
    TextResponse,
)
from integrations.chat.runtime import ChatRuntime, normalize_action


class FakeAdapter:
    provider = "fake"
    tenant_id = "tenant"
    conversation_id = "room"

    def __init__(self, *, files: bool = True, delete: bool = True) -> None:
        self.capabilities = ChatCapabilities(
            max_text_length=100,
            supports_files=files,
            supports_delete=delete,
        )
        self.batch = InboundBatch((), "cursor")
        self.texts: list[tuple[str, str]] = []
        self.files: list[tuple[FileResponse, str]] = []
        self.clear_calls = 0

    def receive(self, cursor: str) -> InboundBatch:
        return self.batch

    def send_text(self, response: TextResponse, *, thread_id: str = "") -> None:
        self.texts.append((response.text, thread_id))

    def send_file(self, response: FileResponse, *, thread_id: str = "") -> None:
        self.files.append((response, thread_id))

    def clear_conversation(self) -> tuple[int, int]:
        self.clear_calls += 1
        return 3, 1


def message(user: str, message_id: str, text: str, *, thread: str = "") -> InboundMessage:
    return InboundMessage(
        provider="fake",
        tenant_id="tenant",
        conversation_id="room",
        thread_id=thread,
        message_id=message_id,
        external_user_id=user,
        text=text,
        timestamp="2026-08-29T00:00:00Z",
    )


class ActionNormalizationTests(unittest.TestCase):
    def test_legacy_router_results_are_normalized(self) -> None:
        self.assertEqual(normalize_action("hello"), TextResponse("hello"))
        self.assertEqual(normalize_action({"autoplay": 1.5}), StartDemo(1.5))
        self.assertEqual(normalize_action({"clear_history": True}), ClearConversation())
        self.assertEqual(
            normalize_action(
                {"upload": {"filename": "x.csv", "content": b"x", "ctype": "text/csv"}}
            ),
            FileResponse("x.csv", b"x", "text/csv"),
        )


class ChatRuntimeTests(unittest.TestCase):
    def test_sessions_are_isolated_by_user_and_thread(self) -> None:
        adapter = FakeAdapter()

        def handler(text: str, state: dict) -> str:
            state["count"] += 1
            return f"{text}:{state['count']}"

        runtime = ChatRuntime(adapter, handler, lambda: {"count": 0})
        runtime.dispatch(message("alice", "1", "a", thread="one"))
        runtime.dispatch(message("bob", "2", "b", thread="one"))
        runtime.dispatch(message("alice", "3", "a", thread="two"))
        runtime.dispatch(message("alice", "4", "a", thread="one"))

        self.assertEqual(
            [text for text, _thread in adapter.texts],
            ["a:1", "b:1", "a:1", "a:2"],
        )

    def test_poll_suppresses_duplicate_provider_delivery(self) -> None:
        adapter = FakeAdapter()
        duplicate = message("alice", "same-id", "hello")
        adapter.batch = InboundBatch((duplicate, duplicate), "next")
        calls: list[str] = []
        runtime = ChatRuntime(adapter, lambda text, _state: calls.append(text), dict)

        self.assertEqual(runtime.poll_once("old"), "next")
        self.assertEqual(calls, ["hello"])

    def test_file_action_has_safe_capability_fallback(self) -> None:
        adapter = FakeAdapter(files=False)
        runtime = ChatRuntime(
            adapter,
            lambda _text, _state: FileResponse("x.txt", b"x", "text/plain"),
            dict,
        )

        runtime.dispatch(message("alice", "1", "file"))

        self.assertEqual(adapter.files, [])
        self.assertIn("does not support file delivery", adapter.texts[0][0])

    def test_clear_removes_only_current_session(self) -> None:
        adapter = FakeAdapter()

        def handler(text: str, state: dict) -> object:
            if text == "clear":
                return ClearConversation()
            state["count"] = state.get("count", 0) + 1
            return str(state["count"])

        runtime = ChatRuntime(adapter, handler, dict)
        runtime.dispatch(message("alice", "1", "count"))
        runtime.dispatch(message("alice", "2", "clear"))
        runtime.dispatch(message("alice", "3", "count"))

        self.assertEqual(adapter.clear_calls, 1)
        self.assertEqual(adapter.texts[0][0], "1")
        self.assertEqual(adapter.texts[-1][0], "1")

    def test_demo_callback_receives_session_snapshot(self) -> None:
        adapter = FakeAdapter()
        starts: list[tuple[float, dict]] = []
        runtime = ChatRuntime(
            adapter,
            lambda _text, state: (state.update(role="curator"), StartDemo(0.5))[1],
            dict,
            start_demo=lambda delay, state: starts.append((delay, state)),
        )

        runtime.dispatch(message("alice", "1", "demo"))

        self.assertEqual(starts, [(0.5, {"role": "curator"})])


if __name__ == "__main__":
    unittest.main()
