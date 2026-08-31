"""Opaque, in-memory fixture sessions for the loopback Workbench demo."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from typing import Mapping

SESSION_COOKIE = "saleswiki_demo_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class DemoPersona:
    id: str
    name: str
    role: str
    team: str

    def public(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "role": self.role, "team": self.team}


class DemoSessionStore:
    """Session state only; it is never production authentication."""

    def __init__(self, default_actor_id: str, personas: Mapping[str, DemoPersona]) -> None:
        if default_actor_id not in personas:
            raise ValueError("default fixture actor must be configured")
        self._default_actor_id = default_actor_id
        self._personas = dict(personas)
        self._sessions: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def resolve(self, cookie_header: str) -> tuple[str, str | None]:
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except (CookieError, ValueError):
            return self._default_actor_id, None
        token = cookie.get(SESSION_COOKIE)
        if token is None:
            return self._default_actor_id, None
        session_id = token.value
        with self._lock:
            item = self._sessions.get(session_id)
            if not item or item[1] < time.monotonic():
                self._sessions.pop(session_id, None)
                return self._default_actor_id, None
            return item[0], session_id

    def create(self) -> tuple[str, str]:
        session_id = uuid.uuid4().hex + uuid.uuid4().hex
        with self._lock:
            self._sessions[session_id] = (self._default_actor_id, time.monotonic() + SESSION_TTL_SECONDS)
        return self._default_actor_id, session_id

    def switch(self, session_id: str, actor_id: str) -> str | None:
        if actor_id not in self._personas:
            return None
        with self._lock:
            item = self._sessions.get(session_id)
            if not item or item[1] < time.monotonic():
                self._sessions.pop(session_id, None)
                return None
            self._sessions[session_id] = (actor_id, time.monotonic() + SESSION_TTL_SECONDS)
        return actor_id
