"""Identity resolution. Role is resolved server-side, never chosen by the client.

Slice 1 uses a fixture provider keyed by an actor id (from a server session/env).
Google OIDC will later implement the same IdentityProvider protocol.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Protocol


@dataclass(frozen=True)
class Actor:
    id: str
    role: str
    team: str = ""
    email: str = ""
    name: str = ""
    owns: tuple[str, ...] = field(default_factory=tuple)


class IdentityProvider(Protocol):
    def resolve(self) -> Actor: ...


class FixtureIdentityProvider:
    """Resolves a demo Actor from the fixture provider in identity-provider.json."""

    def __init__(self, actor_id: str, identity_config: dict) -> None:
        self._actor_id = actor_id
        self._config = identity_config

    @classmethod
    def from_env(cls, identity_config: dict, env: Mapping[str, str] | None = None) -> "FixtureIdentityProvider":
        env = env if env is not None else os.environ
        key = identity_config.get("session_actor_env", "SALESWIKI_DEMO_ACTOR")
        actor_id = env.get(key, "")
        return cls(actor_id, identity_config)

    def resolve(self) -> Actor:
        users = self._config.get("providers", {}).get("fixture", {}).get("users", [])
        for user in users:
            if user.get("id") == self._actor_id:
                return Actor(
                    id=user["id"],
                    role=user["role"],
                    team=user.get("team", ""),
                    email=user.get("email", ""),
                    name=user.get("name", ""),
                    owns=tuple(user.get("owns", [])),
                )
        raise KeyError(f"unknown fixture actor: {self._actor_id!r}")
