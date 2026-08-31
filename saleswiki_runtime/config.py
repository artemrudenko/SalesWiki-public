"""Typed, secret-safe runtime configuration for SalesWiki integrations."""

from __future__ import annotations

import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
TRUE_VALUES = {"1", "true", "yes", "on"}


class ConfigError(ValueError):
    """Raised when a runtime profile is incomplete or unsafe."""


def _bool_env(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    value = env.get(name)
    return default if value is None else value.strip().lower() in TRUE_VALUES


def _table(data: dict, key: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"`{key}` must be a TOML table")
    return value


def _string(data: dict, key: str, default: str = "") -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"`{key}` must be a string")
    return value.strip()


def _strings(data: dict, key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigError(f"`{key}` must be an array of strings")
    return tuple(item.strip() for item in value if item.strip())


def _resolve_path(value: str, base: Path) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def _env_ref(value: str, field_name: str) -> str:
    if value and not ENV_NAME.fullmatch(value):
        raise ConfigError(f"`{field_name}` must name an environment variable")
    return value


def _origin(value: str) -> str:
    if not value or any(char in value for char in "\r\n"):
        raise ConfigError("workbench.allowed_origins contains an invalid origin")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConfigError("workbench.allowed_origins contains an invalid port") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ConfigError("workbench.allowed_origins must contain exact http(s) origins")
    return value.rstrip("/")


@dataclass(frozen=True)
class VaultSettings:
    root: Path | None = None
    runtime: Path | None = None


@dataclass(frozen=True)
class FeatureSettings:
    use_mcp: bool = False
    llm_summary: bool = False
    llm_recommendations: bool = False


@dataclass(frozen=True)
class AdapterSettings:
    name: str
    provider: str
    enabled: bool
    mode: str
    identity_provider: str
    conversation: str = ""
    direct_message: str = ""
    endpoint_env: str = ""
    user_env: str = ""
    password_env: str = ""
    token_env: str = ""
    trigger: str = ""
    poll_seconds: float = 2.0

    def env_value(self, env: Mapping[str, str], ref: str) -> str:
        return env.get(ref, "").strip() if ref else ""

    def missing_secret_refs(self, env: Mapping[str, str]) -> list[str]:
        refs = (self.endpoint_env, self.user_env, self.password_env, self.token_env)
        return [ref for ref in refs if ref and not env.get(ref, "").strip()]


@dataclass(frozen=True)
class ChatSettings:
    session_store: str = "memory"
    default_trigger: str = "?"
    adapters: tuple[AdapterSettings, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkbenchSettings:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8787
    identity_provider: str = "fixture"
    mcp_transport: str = "stdio"
    allowed_origins: tuple[str, ...] = field(default_factory=tuple)
    timeout_seconds: float = 15.0
    max_concurrent_requests: int = 4
    # Only meaningful for the isolated fixture/demo BFF.  It must never turn a
    # browser into an identity provider for a shared deployment.
    allow_fixture_persona_switching: bool = False


@dataclass(frozen=True)
class RuntimeSettings:
    version: int
    profile: str
    vault: VaultSettings
    features: FeatureSettings
    chat: ChatSettings
    workbench: WorkbenchSettings
    source: str

    def enabled_adapter(self, provider: str) -> AdapterSettings:
        matches = [a for a in self.chat.adapters if a.enabled and a.provider == provider]
        if len(matches) != 1:
            raise ConfigError(
                f"expected exactly one enabled `{provider}` adapter; found {len(matches)}"
            )
        return matches[0]

    def redacted(self, env: Mapping[str, str] | None = None) -> dict:
        env = env if env is not None else os.environ
        adapters = []
        for adapter in self.chat.adapters:
            refs = {
                key: ref
                for key, ref in {
                    "endpoint": adapter.endpoint_env,
                    "user": adapter.user_env,
                    "password": adapter.password_env,
                    "token": adapter.token_env,
                }.items()
                if ref
            }
            adapters.append(
                {
                    "name": adapter.name,
                    "provider": adapter.provider,
                    "enabled": adapter.enabled,
                    "mode": adapter.mode,
                    "identity_provider": adapter.identity_provider,
                    "conversation": adapter.conversation,
                    "direct_message": adapter.direct_message,
                    "trigger": adapter.trigger or self.chat.default_trigger,
                    "poll_seconds": adapter.poll_seconds,
                    "secret_refs": {
                        key: {"env": ref, "present": bool(env.get(ref, "").strip())}
                        for key, ref in refs.items()
                    },
                }
            )
        return {
            "version": self.version,
            "profile": self.profile,
            "source": self.source,
            "vault": {
                "root": str(self.vault.root) if self.vault.root else None,
                "runtime": str(self.vault.runtime) if self.vault.runtime else None,
            },
            "features": {
                "use_mcp": self.features.use_mcp,
                "llm_summary": self.features.llm_summary,
                "llm_recommendations": self.features.llm_recommendations,
            },
            "chat": {
                "session_store": self.chat.session_store,
                "default_trigger": self.chat.default_trigger,
                "adapters": adapters,
            },
            "workbench": {
                "enabled": self.workbench.enabled,
                "host": self.workbench.host,
                "port": self.workbench.port,
                "identity_provider": self.workbench.identity_provider,
                "mcp_transport": self.workbench.mcp_transport,
                "allowed_origins": list(self.workbench.allowed_origins),
                "timeout_seconds": self.workbench.timeout_seconds,
                "max_concurrent_requests": self.workbench.max_concurrent_requests,
                "allow_fixture_persona_switching": self.workbench.allow_fixture_persona_switching,
            },
        }


def _parse_adapter(name: str, raw: dict, default_trigger: str) -> AdapterSettings:
    provider = _string(raw, "provider")
    if not provider:
        raise ConfigError(f"chat adapter `{name}` requires `provider`")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError(f"chat adapter `{name}` field `enabled` must be boolean")
    poll = raw.get("poll_seconds", 2.0)
    if not isinstance(poll, (int, float)) or isinstance(poll, bool) or poll <= 0:
        raise ConfigError(f"chat adapter `{name}` field `poll_seconds` must be positive")
    adapter = AdapterSettings(
        name=name,
        provider=provider,
        enabled=enabled,
        mode=_string(raw, "mode", "poll"),
        identity_provider=_string(raw, "identity_provider", "fixture"),
        conversation=_string(raw, "conversation"),
        direct_message=_string(raw, "direct_message"),
        endpoint_env=_env_ref(_string(raw, "url_env"), f"{name}.url_env"),
        user_env=_env_ref(_string(raw, "user_env"), f"{name}.user_env"),
        password_env=_env_ref(_string(raw, "password_env"), f"{name}.password_env"),
        token_env=_env_ref(_string(raw, "token_env"), f"{name}.token_env"),
        trigger=_string(raw, "trigger", default_trigger),
        poll_seconds=float(poll),
    )
    if adapter.enabled and adapter.provider == "rocketchat":
        if not adapter.endpoint_env or not adapter.user_env or not adapter.password_env:
            raise ConfigError(
                f"enabled Rocket.Chat adapter `{name}` requires url_env, user_env and password_env"
            )
        if bool(adapter.conversation) == bool(adapter.direct_message):
            raise ConfigError(
                f"enabled Rocket.Chat adapter `{name}` requires exactly one of conversation or direct_message"
            )
    return adapter


def parse_runtime_settings(path: Path) -> RuntimeSettings:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"runtime config not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    version = raw.get("version")
    if version != 1:
        raise ConfigError("runtime config `version` must be 1")
    profile = _string(raw, "profile", "demo")
    if profile not in {"demo", "pilot", "production"}:
        raise ConfigError("runtime config `profile` must be demo, pilot or production")

    base = path.resolve().parent
    vault_raw = _table(raw, "vault")
    vault = VaultSettings(
        root=_resolve_path(_string(vault_raw, "root"), base),
        runtime=_resolve_path(_string(vault_raw, "runtime"), base),
    )
    features_raw = _table(raw, "features")
    feature_values = {}
    for key in ("use_mcp", "llm_summary", "llm_recommendations"):
        value = features_raw.get(key, False)
        if not isinstance(value, bool):
            raise ConfigError(f"features.{key} must be boolean")
        feature_values[key] = value
    features = FeatureSettings(**feature_values)

    chat_raw = _table(raw, "chat")
    default_trigger = _string(chat_raw, "default_trigger", "?")
    if not default_trigger:
        raise ConfigError("chat.default_trigger must not be empty")
    adapters_raw = _table(chat_raw, "adapters")
    adapters = tuple(
        _parse_adapter(name, value, default_trigger)
        for name, value in sorted(adapters_raw.items())
        if isinstance(value, dict)
    )
    if len(adapters) != len(adapters_raw):
        raise ConfigError("every chat.adapters entry must be a TOML table")
    if profile != "demo" and any(a.enabled and a.identity_provider == "fixture" for a in adapters):
        raise ConfigError("fixture identity is allowed only in the demo profile")

    workbench_raw = _table(raw, "workbench")
    workbench_enabled = workbench_raw.get("enabled", False)
    if not isinstance(workbench_enabled, bool):
        raise ConfigError("workbench.enabled must be boolean")
    workbench_port = workbench_raw.get("port", 8787)
    if isinstance(workbench_port, bool) or not isinstance(workbench_port, int) or not 1 <= workbench_port <= 65535:
        raise ConfigError("workbench.port must be an integer from 1 to 65535")
    workbench_identity = _string(workbench_raw, "identity_provider", "fixture")
    workbench_transport = _string(workbench_raw, "mcp_transport", "stdio")
    if workbench_transport != "stdio":
        raise ConfigError("workbench.mcp_transport currently supports only stdio")
    if workbench_enabled and profile != "demo" and workbench_identity == "fixture":
        raise ConfigError("fixture Workbench identity is allowed only in the demo profile")
    workbench_timeout = workbench_raw.get("timeout_seconds", 15.0)
    if (
        isinstance(workbench_timeout, bool)
        or not isinstance(workbench_timeout, (int, float))
        or not 1 <= workbench_timeout <= 30
    ):
        raise ConfigError("workbench.timeout_seconds must be from 1 to 30")
    workbench_concurrency = workbench_raw.get("max_concurrent_requests", 4)
    if (
        isinstance(workbench_concurrency, bool)
        or not isinstance(workbench_concurrency, int)
        or not 1 <= workbench_concurrency <= 8
    ):
        raise ConfigError("workbench.max_concurrent_requests must be an integer from 1 to 8")
    persona_switching = workbench_raw.get("allow_fixture_persona_switching", False)
    if not isinstance(persona_switching, bool):
        raise ConfigError("workbench.allow_fixture_persona_switching must be boolean")
    if persona_switching and (profile != "demo" or workbench_identity != "fixture"):
        raise ConfigError("fixture persona switching is allowed only for the demo fixture Workbench")
    workbench = WorkbenchSettings(
        enabled=workbench_enabled,
        host=_string(workbench_raw, "host", "127.0.0.1"),
        port=workbench_port,
        identity_provider=workbench_identity,
        mcp_transport=workbench_transport,
        allowed_origins=tuple(_origin(item) for item in _strings(workbench_raw, "allowed_origins")),
        timeout_seconds=float(workbench_timeout),
        max_concurrent_requests=workbench_concurrency,
        allow_fixture_persona_switching=persona_switching,
    )
    return RuntimeSettings(
        version=version,
        profile=profile,
        vault=vault,
        features=features,
        chat=ChatSettings(
            session_store=_string(chat_raw, "session_store", "memory"),
            default_trigger=default_trigger,
            adapters=adapters,
        ),
        workbench=workbench,
        source=str(path.resolve()),
    )


def _legacy_settings(env: Mapping[str, str]) -> RuntimeSettings:
    channel = env.get("RC_CHANNEL", "").strip()
    dm = env.get("RC_DM", "").strip()
    if not (env.get("RC_URL", "").strip() and env.get("RC_USER", "").strip()
            and env.get("RC_PASS", "") and (channel or dm)):
        raise ConfigError(
            "set SALESWIKI_CONFIG or legacy RC_URL, RC_USER, RC_PASS and RC_CHANNEL/RC_DM"
        )
    if bool(channel) == bool(dm):
        raise ConfigError("legacy runtime requires exactly one of RC_CHANNEL or RC_DM")
    try:
        poll_seconds = float(env.get("RC_POLL", "2"))
    except ValueError as exc:
        raise ConfigError("RC_POLL must be a positive number") from exc
    if poll_seconds <= 0:
        raise ConfigError("RC_POLL must be a positive number")
    adapter = AdapterSettings(
        name="legacy-rocketchat",
        provider="rocketchat",
        enabled=True,
        mode="poll",
        identity_provider="fixture",
        conversation=channel,
        direct_message=dm,
        endpoint_env="RC_URL",
        user_env="RC_USER",
        password_env="RC_PASS",
        trigger=env.get("RC_TRIGGER", "?").strip() or "?",
        poll_seconds=poll_seconds,
    )
    return RuntimeSettings(
        version=1,
        profile="demo",
        vault=VaultSettings(
            root=_resolve_path(env.get("SALESWIKI_DEMO_VAULT", "").strip(), Path.cwd()),
            runtime=_resolve_path(env.get("SALESWIKI_RUNTIME_DIR", "").strip(), Path.cwd()),
        ),
        features=FeatureSettings(
            use_mcp=_bool_env(env, "RC_USE_MCP"),
            llm_summary=_bool_env(env, "RC_LLM_SUMMARY"),
            llm_recommendations=_bool_env(env, "RC_LLM_RECS"),
        ),
        chat=ChatSettings(default_trigger=adapter.trigger, adapters=(adapter,)),
        workbench=WorkbenchSettings(),
        source="legacy environment",
    )


def load_runtime_settings(
    path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    *,
    allow_legacy: bool = True,
) -> RuntimeSettings:
    env = env if env is not None else os.environ
    selected = str(path or env.get("SALESWIKI_CONFIG", "")).strip()
    if selected:
        return parse_runtime_settings(Path(selected).expanduser())
    if allow_legacy:
        settings = _legacy_settings(env)
        print(
            "[warn] RC_* runtime configuration is deprecated; set SALESWIKI_CONFIG instead.",
            file=sys.stderr,
        )
        return settings
    raise ConfigError("SALESWIKI_CONFIG is not set")
