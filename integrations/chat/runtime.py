"""Application-action dispatcher shared by custom chat transports."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from .adapters.base import ChatAdapter
from .models import (
    ChatAction,
    ClearConversation,
    FileResponse,
    InboundMessage,
    NoReply,
    StartDemo,
    TextResponse,
)
from .sessions import MemorySessionStore


def normalize_action(value: object) -> ChatAction:
    """Compatibility boundary for the existing command router."""
    if value is None:
        return NoReply()
    if isinstance(value, (TextResponse, FileResponse, StartDemo, ClearConversation, NoReply)):
        return value
    if isinstance(value, str):
        return TextResponse(value)
    if isinstance(value, dict) and "upload" in value:
        artifact = value["upload"]
        return FileResponse(
            filename=artifact["filename"],
            content=artifact["content"],
            content_type=artifact["ctype"],
            caption=artifact.get("caption", ""),
        )
    if isinstance(value, dict) and "autoplay" in value:
        return StartDemo(float(value["autoplay"]))
    if isinstance(value, dict) and value.get("clear_history") is True:
        return ClearConversation()
    raise TypeError(f"unsupported chat action: {type(value).__name__}")


class ChatRuntime:
    def __init__(
        self,
        adapter: ChatAdapter,
        handler: Callable[[str, dict], object],
        session_factory: Callable[[], dict],
        *,
        sessions: MemorySessionStore | None = None,
        decorate_text: Callable[[str], str] | None = None,
        start_demo: Callable[[float, dict], None] | None = None,
        idempotency_window: int = 2_000,
    ) -> None:
        if idempotency_window < 1:
            raise ValueError("idempotency_window must be positive")
        self.adapter = adapter
        self.handler = handler
        self.session_factory = session_factory
        self.sessions = sessions or MemorySessionStore()
        self.decorate_text = decorate_text or (lambda text: text)
        self.start_demo = start_demo
        self._seen_ids: set[str] = set()
        self._seen_order: deque[str] = deque()
        self._idempotency_window = idempotency_window

    def _accept_once(self, message_id: str) -> bool:
        """Suppress provider retries while keeping memory usage bounded."""
        if message_id in self._seen_ids:
            return False
        self._seen_ids.add(message_id)
        self._seen_order.append(message_id)
        while len(self._seen_order) > self._idempotency_window:
            expired = self._seen_order.popleft()
            self._seen_ids.discard(expired)
        return True

    def dispatch(self, message: InboundMessage) -> ChatAction:
        state = self.sessions.get(message.session_key, self.session_factory)
        action = normalize_action(self.handler(message.text, state))
        if isinstance(action, TextResponse):
            self.adapter.send_text(
                TextResponse(self.decorate_text(action.text)), thread_id=message.thread_id
            )
        elif isinstance(action, FileResponse):
            if not self.adapter.capabilities.supports_files:
                self.adapter.send_text(
                    TextResponse("This chat provider does not support file delivery."),
                    thread_id=message.thread_id,
                )
            else:
                self.adapter.send_file(action, thread_id=message.thread_id)
        elif isinstance(action, StartDemo):
            if self.start_demo is None:
                self.adapter.send_text(
                    TextResponse("This chat provider does not support demo autoplay."),
                    thread_id=message.thread_id,
                )
            else:
                self.start_demo(action.delay_seconds, dict(state))
        elif isinstance(action, ClearConversation):
            if not self.adapter.capabilities.supports_delete:
                self.adapter.send_text(
                    TextResponse("This chat provider cannot clear conversation history."),
                    thread_id=message.thread_id,
                )
            else:
                deleted, skipped = self.adapter.clear_conversation()
                self.sessions.clear(message.session_key)
                self.adapter.send_text(
                    TextResponse(f"🧹 History cleared: deleted {deleted}, skipped {skipped}."),
                    thread_id=message.thread_id,
                )
        return action

    def poll_once(self, cursor: str) -> str:
        batch = self.adapter.receive(cursor)
        for message in batch.messages:
            if self._accept_once(message.message_id):
                self.dispatch(message)
        return batch.cursor
