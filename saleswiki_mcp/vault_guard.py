"""Fail-closed guard: a fixture-identity or self-asserted-role surface must never
serve a production-shaped vault.

The MCP gateway resolves one fixture actor per process and the Rocket.Chat bridge
lets a channel member self-assert a role — neither is real authentication. Pointed
at a production vault, either would expose real data under a made-up identity
without a real SSO boundary. A demo/synthetic vault is safe because its contents
are fake. This module refuses anything that is not demonstrably a demo vault,
unless an operator sets an explicit override env var and accepts the risk.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import frontmatter

ALLOW_PROD_ENV = "SALESWIKI_ALLOW_PROD_VAULT"
_TRUE = ("1", "true", "yes", "on")


def _override_enabled() -> bool:
    return os.environ.get(ALLOW_PROD_ENV, "").strip().lower() in _TRUE


def is_demo_vault(vault_root) -> bool:
    """True iff the vault has cards and none looks like real (pilot/production) data.

    A card counts as demo when it carries `dataset: demo` or `synthetic: true`. An
    explicit `dataset: pilot`/`production` card fails the check immediately. Cards
    with no dataset marker at all (e.g. an index or log page) are tolerated, but at
    least one card must be positively marked demo — an empty or unmarked vault is
    treated as not-demo, so the guard fails closed on a production vault that simply
    omits the markers.
    """
    root = Path(vault_root)
    if not root.exists():
        return False
    has_demo = False
    for path in root.rglob("*.md"):
        try:
            props, _ = frontmatter.parse(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # An unreadable or undecodable (non-UTF-8) card must not be silently
            # skipped: it could be the very `dataset: production`/`pilot` marker
            # that should disqualify the vault. Deny on doubt (fail closed) rather
            # than serving the readable remainder. UnicodeDecodeError is a
            # ValueError, so this also stops a binary card from crashing the guard.
            return False
        dataset = str(props.get("dataset", "")).strip().lower()
        synthetic = str(props.get("synthetic", "")).strip().lower() in _TRUE
        if dataset in ("pilot", "production", "prod"):
            return False
        if dataset == "demo" or synthetic:
            has_demo = True
    return has_demo


def require_demo_vault(vault_root, *, context: str) -> None:
    """Raise unless `vault_root` is a demo vault or the override env var is set."""
    if _override_enabled():
        return
    if not is_demo_vault(vault_root):
        raise RuntimeError(
            f"{context}: refusing to serve a vault that is not marked demo/synthetic "
            f"({vault_root}). This surface uses fixture / self-asserted identity, which "
            f"is not real authentication, so it must never run against real data. If you "
            f"genuinely mean to, set {ALLOW_PROD_ENV}=1 after reviewing "
            f"docs/engineering/permissioned-knowledge-sso-design.md."
        )
