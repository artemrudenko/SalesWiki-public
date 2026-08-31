"""Operator CLI for runtime configuration and read-only diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from saleswiki_mcp import config as contracts
from saleswiki_mcp import vault_guard
from saleswiki_mcp.identity import FixtureIdentityProvider

from .config import ConfigError, RuntimeSettings, load_runtime_settings


def _load(path: str) -> RuntimeSettings:
    return load_runtime_settings(path or None, allow_legacy=not bool(path))


def _doctor(settings: RuntimeSettings) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    try:
        contracts.access_policy()
        contracts.boundary_registry()
        contracts.identity_config()
        contracts.field_extraction()
        passed.append("machine-readable policy contracts load")
    except Exception as exc:
        failed.append(f"policy contracts: {exc}")

    if settings.vault.root is None:
        failed.append("vault.root is not configured")
    elif not settings.vault.root.is_dir():
        failed.append(f"vault root does not exist: {settings.vault.root}")
    else:
        passed.append(f"vault root exists: {settings.vault.root}")
        fixture_active = (
            any(a.enabled and a.identity_provider == "fixture" for a in settings.chat.adapters)
            or (
                settings.workbench.enabled
                and settings.workbench.identity_provider == "fixture"
            )
        )
        if fixture_active:
            try:
                vault_guard.require_demo_vault(settings.vault.root, context="runtime doctor")
                passed.append("fixture identity is restricted to a demo vault")
            except Exception as exc:
                failed.append(str(exc))

    if settings.workbench.enabled and settings.workbench.identity_provider == "fixture":
        try:
            actor = FixtureIdentityProvider.from_env(contracts.identity_config()).resolve()
            passed.append(f"Workbench fixture actor resolves: {actor.id}")
        except Exception:
            failed.append("Workbench fixture actor is missing or unknown")

    runtime = settings.vault.runtime
    runtime_parent = runtime
    while runtime_parent is not None and not runtime_parent.exists():
        parent = runtime_parent.parent
        runtime_parent = None if parent == runtime_parent else parent
    if runtime is None or runtime_parent is None:
        failed.append("vault.runtime is not configured")
    elif not os.access(runtime_parent, os.W_OK):
        failed.append(f"runtime path cannot be created under: {runtime_parent}")
    else:
        passed.append(f"runtime path is writable or creatable: {runtime}")

    for adapter in settings.chat.adapters:
        if not adapter.enabled:
            continue
        missing = adapter.missing_secret_refs(os.environ)
        if missing:
            failed.append(f"adapter {adapter.name} missing environment values: {', '.join(missing)}")
        else:
            passed.append(f"adapter {adapter.name} has required environment values")
    return passed, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SalesWiki runtime configuration tools")
    parser.add_argument("--config", default="", help="runtime TOML path (or set SALESWIKI_CONFIG)")
    commands = parser.add_subparsers(dest="command", required=True)
    config_cmd = commands.add_parser("config")
    config_actions = config_cmd.add_subparsers(dest="config_action", required=True)
    config_actions.add_parser("validate")
    config_actions.add_parser("show").add_argument("--redacted", action="store_true")
    commands.add_parser("doctor")
    args = parser.parse_args(argv)

    try:
        settings = _load(args.config)
        if args.command == "config" and args.config_action == "validate":
            print(f"OK: runtime config is valid ({settings.source})")
            return 0
        if args.command == "config" and args.config_action == "show":
            if not args.redacted:
                print("Refusing unredacted configuration output; pass --redacted.", file=sys.stderr)
                return 2
            print(json.dumps(settings.redacted(), indent=2, sort_keys=True))
            return 0
        passed, failed = _doctor(settings)
        for item in passed:
            print(f"PASS: {item}")
        for item in failed:
            print(f"FAIL: {item}")
        return 1 if failed else 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
