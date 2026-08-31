"""Narrow protocol implemented by custom chat transports."""

from __future__ import annotations

from typing import Protocol

from ..models import ChatCapabilities, FileResponse, InboundBatch, TextResponse


class ChatAdapter(Protocol):
    provider: str
    tenant_id: str
    conversation_id: str
    capabilities: ChatCapabilities

    def receive(self, cursor: str) -> InboundBatch: ...

    def send_text(self, response: TextResponse, *, thread_id: str = "") -> None: ...

    def send_file(self, response: FileResponse, *, thread_id: str = "") -> None: ...

    def clear_conversation(self) -> tuple[int, int]: ...
