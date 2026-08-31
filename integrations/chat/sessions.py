"""Conversation-scoped state stores."""

from __future__ import annotations

from collections.abc import Callable

from .models import ConversationKey


class MemorySessionStore:
    """Process-local demo store keyed by provider, tenant, thread and user."""

    def __init__(self) -> None:
        self._sessions: dict[ConversationKey, dict] = {}

    def get(self, key: ConversationKey, factory: Callable[[], dict]) -> dict:
        if key not in self._sessions:
            self._sessions[key] = factory()
        return self._sessions[key]

    def clear(self, key: ConversationKey) -> None:
        self._sessions.pop(key, None)
