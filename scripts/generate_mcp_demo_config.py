#!/usr/bin/env python3
"""One-command launcher for the Cowork / multi-MCP demo track.

Prepares a shared permissioned demo vault (or validates an existing one) and
emits a ready-to-paste `mcpServers` JSON config with one SalesWiki MCP server
entry per persona. All entries share the same vault and the same runtime
directory, so proposals/grants approved through one persona's server are
visible to the others (the governed loop works across chats).

The emitted `command` reflects the real invocation: the gateway needs the
`mcp` SDK, so it runs under this repo's `.venv/bin/python`, and because
`saleswiki_mcp/server.py` uses package-relative imports it must be started as
`-m saleswiki_mcp.server` with `PYTHONPATH` set to the repo root (MCP clients
such as Claude Desktop / Cowork do not set a working directory).

Standard-library only. Read/emit only: it never touches production cards.

Usage:
    python3 scripts/generate_mcp_demo_config.py --personas ae,marketing,curator [--out FILE] [--vault DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_demo_vault as gdv  # noqa: E402

# Persona alias -> fixture actor id (schemas/identity-provider.json). The role
# is resolved server-side from SALESWIKI_DEMO_ACTOR; the client never picks it.
PERSONA_ACTORS: dict[str, str] = {
    "ae": "demo-ethan-ae",
    "marketing": "demo-olivia-marketing",
    "curator": "demo-sophie-curator",
    "hos": "demo-claire-hos",
    "revops": "demo-raj-revops",
    "admin": "demo-ada-admin",
    "legal": "demo-hannah-legal",
    "sdr": "demo-sam-sdr",
    "sales": "demo-sam-sdr",
    "viewer": "demo-broad-viewer",
    "employee": "demo-broad-viewer",
}

# Physical permission boundaries a permissioned demo vault must contain
# (created by generate_demo_vault.generate_permissioned_demo, mapped by
# schemas/boundary-registry.json).
BOUNDARY_DIRS: tuple[str, str, str] = ("broad", "sales-confidential", "personal-data")

# Stable, user-visible default location (delete the whole folder to reset).
# health_check's demo-boundary scan covers demo/demo-vault and demo/permissioned
# only, so this extra synthetic sub-vault does not interfere with it.
DEFAULT_BASE = ROOT / "demo" / "mcp-demo"

VENV_HINT = "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"


class ServerEntry(TypedDict):
    """One `mcpServers` entry: how the client launches a persona's gateway."""

    command: str
    args: list[str]
    env: dict[str, str]


class McpConfig(TypedDict):
    mcpServers: dict[str, ServerEntry]


def parse_personas(raw: str) -> list[str]:
    """Split a comma-separated persona list; dedupe; reject unknown aliases."""
    personas: list[str] = []
    for token in raw.split(","):
        alias = token.strip().lower()
        if not alias:
            continue
        if alias not in PERSONA_ACTORS:
            known = ", ".join(sorted(PERSONA_ACTORS))
            raise ValueError(f"unknown persona {alias!r}; known personas: {known}")
        if alias not in personas:
            personas.append(alias)
    if not personas:
        raise ValueError("no personas given; pass e.g. --personas ae,marketing,curator")
    return personas


def validate_vault(vault: Path) -> None:
    """Ensure the directory looks like a permissioned *demo* vault.

    The multi-persona config puts requester and approver personas on one vault, so
    a single client session can complete request_access -> approve_proposal with no
    distinct human approver (a separation-of-duties collapse). That is acceptable
    only against synthetic data, so this fails closed on a non-demo vault the same
    way the gateway and bridge do.
    """
    if not vault.is_dir():
        raise ValueError(f"vault directory not found: {vault}")
    missing = [name for name in BOUNDARY_DIRS if not (vault / name).is_dir()]
    if missing:
        raise ValueError(
            f"{vault} does not look like a permissioned demo vault: missing boundary "
            f"folders {', '.join(missing)}. Generate one with "
            "scripts/generate_demo_vault.py or omit --vault to create a fresh one."
        )
    from saleswiki_mcp import vault_guard

    vault_guard.require_demo_vault(vault, context="multi-persona MCP demo config")


def prepare_vault(vault_arg: str | None) -> tuple[Path, Path]:
    """Return (vault_root, runtime_dir); generate a fresh vault when needed.

    The runtime dir sits next to the vault and is shared by every persona's
    server, so one proposals.jsonl/audit.jsonl carries the governance loop
    across all of them.
    """
    if vault_arg:
        vault = Path(vault_arg).expanduser().resolve()
        validate_vault(vault)
        runtime = vault.parent / "runtime"
    else:
        vault = (DEFAULT_BASE / "permissioned").resolve()
        gdv.generate_permissioned_demo(vault)
        runtime = (DEFAULT_BASE / "runtime").resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    return vault, runtime


def find_venv_python(root: Path = ROOT) -> Path | None:
    """Absolute path of this repo's venv python (the gateway needs the mcp SDK)."""
    candidate = root / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else None


def build_mcp_config(
    personas: list[str], vault_root: Path, runtime_dir: Path, python_exe: Path
) -> McpConfig:
    """Assemble one shared-vault `mcpServers` entry per persona."""
    servers: dict[str, ServerEntry] = {}
    for persona in personas:
        servers[f"saleswiki-{persona}"] = ServerEntry(
            command=str(python_exe),
            args=["-m", "saleswiki_mcp.server"],
            env={
                "PYTHONPATH": str(ROOT),
                "SALESWIKI_DEMO_ACTOR": PERSONA_ACTORS[persona],
                "SALESWIKI_VAULT_ROOT": str(vault_root.resolve()),
                "SALESWIKI_RUNTIME_DIR": str(runtime_dir.resolve()),
            },
        )
    return McpConfig(mcpServers=servers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--personas",
        required=True,
        help="comma-separated persona list, e.g. ae,marketing,curator "
        f"(known: {', '.join(sorted(PERSONA_ACTORS))})",
    )
    parser.add_argument("--out", help="write the JSON config to FILE instead of stdout")
    parser.add_argument(
        "--vault",
        help="reuse an existing permissioned demo vault directory "
        "(default: generate a fresh one under demo/mcp-demo/)",
    )
    args = parser.parse_args(argv)

    try:
        personas = parse_personas(args.personas)
        vault_root, runtime_dir = prepare_vault(args.vault)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    python_exe = find_venv_python()
    if python_exe is None:
        print(
            "error: .venv not found — the MCP gateway needs the `mcp` SDK.\n"
            f"Create it first: {VENV_HINT}",
            file=sys.stderr,
        )
        return 1

    config = build_mcp_config(personas, vault_root, runtime_dir, python_exe)
    rendered = json.dumps(config, indent=2)

    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote MCP config for {len(personas)} persona(s) to {out}", file=sys.stderr)
    else:
        print(rendered)
        print(
            "\nPaste the `mcpServers` block above into your MCP client config "
            "(Claude Desktop: claude_desktop_config.json; Cowork: project MCP settings), "
            "then restart the client.",
            file=sys.stderr,
        )
    print(f"Shared vault:   {vault_root}", file=sys.stderr)
    print(f"Shared runtime: {runtime_dir} (proposals.jsonl/audit.jsonl flow between personas)", file=sys.stderr)
    if not args.vault:
        print(f"Delete {DEFAULT_BASE} to reset the demo state.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
