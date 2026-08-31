"""Small composition root for the Rocket.Chat-facing SalesWiki adapter."""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

import generate_demo_vault as gdv
from _bridge_answers import WikiAnswerMixin
from _bridge_common import ROLES, now_iso
from _bridge_workflows import WikiWorkflowMixin
from saleswiki_mcp import config, vault_guard
from saleswiki_mcp.identity import FixtureIdentityProvider
from saleswiki_mcp.service import build_default_service
from saleswiki_runtime.config import RuntimeSettings


class Wiki(WikiAnswerMixin, WikiWorkflowMixin):
    def __init__(self, runtime_settings: RuntimeSettings | None = None) -> None:
        self.runtime_settings = runtime_settings
        configured_vault = runtime_settings.vault.root if runtime_settings else None
        existing = str(configured_vault) if configured_vault else os.environ.get("SALESWIKI_DEMO_VAULT")
        if existing:
            vault = Path(existing)
            # Self-asserted chat roles are not authentication (ADR-0016): refuse a
            # vault that is not demo/synthetic so the bridge can never serve real
            # data under a made-up role. An operator who really means to must set
            # SALESWIKI_ALLOW_PROD_VAULT=1.
            vault_guard.require_demo_vault(vault, context="Rocket.Chat bridge (self-asserted role)")
        else:
            tmp = Path(tempfile.mkdtemp(prefix="rc-bridge-demo-"))
            vault = tmp / "permissioned"
            gdv.generate_permissioned_demo(vault)
        configured_runtime = runtime_settings.vault.runtime if runtime_settings else None
        runtime = configured_runtime or Path(tempfile.mkdtemp(prefix="rc-bridge-rt-"))
        runtime.mkdir(parents=True, exist_ok=True)
        self.svc = build_default_service(
            vault, runtime / "audit.jsonl", runtime / "proposals.jsonl", now=now_iso
        )
        self._identity_config = config.identity_config()
        # Optional authentic mode: route reads through the MCP server (server.py)
        # over stdio instead of calling the core in-process. Needs the `mcp` SDK,
        # so run the bridge under .venv/bin/python when RC_USE_MCP=1.
        self.vault_root = vault
        self.runtime = runtime
        self.use_mcp = (
            runtime_settings.features.use_mcp
            if runtime_settings
            else os.environ.get("RC_USE_MCP", "").strip() not in ("", "0", "false")
        )
        # `демо стоп` flips this; the autoplay thread checks it before each beat.
        self.autoplay_stop = threading.Event()

    def actor(self, role: str):
        actor_id = ROLES[role][0]
        return FixtureIdentityProvider(actor_id, self._identity_config).resolve()

    def feature_enabled(self, config_name: str, legacy_env: str) -> bool:
        if self.runtime_settings is not None:
            return bool(getattr(self.runtime_settings.features, config_name))
        return os.environ.get(legacy_env, "").strip().lower() not in ("", "0", "false")
