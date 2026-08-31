"""Provider-neutral messages, capabilities and application actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class ChatCapabilities:
    max_text_length: int
    supports_files: bool = False
    supports_threads: bool = False
    supports_buttons: bool = False
    supports_delete: bool = False


@dataclass(frozen=True)
class ConversationKey:
    provider: str
    tenant_id: str
    conversation_id: str
    thread_id: str
    external_user_id: str


@dataclass(frozen=True)
class InboundMessage:
    provider: str
    tenant_id: str
    conversation_id: str
    thread_id: str
    message_id: str
    external_user_id: str
    text: str
    timestamp: str

    @property
    def session_key(self) -> ConversationKey:
        return ConversationKey(
            provider=self.provider,
            tenant_id=self.tenant_id,
            conversation_id=self.conversation_id,
            thread_id=self.thread_id,
            external_user_id=self.external_user_id,
        )


@dataclass(frozen=True)
class InboundBatch:
    messages: tuple[InboundMessage, ...]
    cursor: str


@dataclass(frozen=True)
class TextResponse:
    text: str


@dataclass(frozen=True)
class FileResponse:
    filename: str
    content: bytes
    content_type: str
    caption: str = ""


@dataclass(frozen=True)
class StartDemo:
    delay_seconds: float


@dataclass(frozen=True)
class ClearConversation:
    pass


@dataclass(frozen=True)
class NoReply:
    pass


ChatAction: TypeAlias = TextResponse | FileResponse | StartDemo | ClearConversation | NoReply
