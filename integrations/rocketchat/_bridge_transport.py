"""Rocket.Chat implementation of the transport-neutral chat adapter protocol."""

from __future__ import annotations

from integrations.chat.models import (
    ChatCapabilities,
    FileResponse,
    InboundBatch,
    InboundMessage,
    TextResponse,
)

from _bridge_client import RocketChat
from _bridge_common import now_iso


class RocketChatTransport:
    provider = "rocketchat"
    capabilities = ChatCapabilities(
        max_text_length=4500,
        supports_files=True,
        supports_threads=False,
        supports_buttons=False,
        supports_delete=True,
    )

    def __init__(
        self,
        client: RocketChat,
        *,
        tenant_id: str,
        conversation_id: str,
        conversation_kind: str,
    ) -> None:
        self.client = client
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.conversation_kind = conversation_kind

    def receive(self, cursor: str) -> InboundBatch:
        messages: list[InboundMessage] = []
        next_cursor = cursor
        for raw in self.client.history(self.conversation_kind, self.conversation_id, cursor):
            timestamp = raw.get("ts", "")
            if not timestamp or timestamp <= cursor:
                continue
            next_cursor = max(next_cursor, timestamp)
            text = raw.get("msg", "")
            if not text:
                continue
            actor = raw.get("u") or {}
            messages.append(
                InboundMessage(
                    provider=self.provider,
                    tenant_id=self.tenant_id,
                    conversation_id=self.conversation_id,
                    thread_id=raw.get("tmid", ""),
                    message_id=raw.get("_id", f"{self.conversation_id}:{timestamp}"),
                    external_user_id=actor.get("_id") or actor.get("username") or "unknown",
                    text=text,
                    timestamp=timestamp,
                )
            )
        return InboundBatch(tuple(messages), next_cursor)

    def send_text(self, response: TextResponse, *, thread_id: str = "") -> None:
        self.client.post(self.conversation_id, response.text)

    def send_file(self, response: FileResponse, *, thread_id: str = "") -> None:
        result = self.client.upload(
            self.conversation_id,
            response.filename,
            response.content,
            response.content_type,
            response.caption,
        )
        if not result.get("success"):
            self.client.post(
                self.conversation_id,
                f"⚠️ Could not upload the file: {result.get('body') or result.get('http')}",
            )

    def clear_conversation(self) -> tuple[int, int]:
        return self.client.clear_history(self.conversation_kind, self.conversation_id)

    def reset_cursor(self) -> str:
        return now_iso()
