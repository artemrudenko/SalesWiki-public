"""Resolve a card's permission boundary from its path under the vault root.

The boundary is decided by physical location (the boundary-registry path map),
not by a YAML label. The card's `boundary:` property is convenience only.
"""

from __future__ import annotations


def resolve_boundary(rel_path: str, registry: dict) -> str:
    """rel_path is POSIX, relative to the configured boundary vault root."""
    rel_path = rel_path.lstrip("/")
    for entry in registry.get("path_map", []):
        prefix = entry.get("prefix", "")
        if prefix and rel_path.startswith(prefix):
            return entry["boundary"]
    # Fail closed: a path outside every known prefix must NOT default to a
    # world-readable boundary. The hard-coded fallback is "quarantine" (a
    # boundary no role lists) so a broken/empty registry also fails closed.
    return registry.get("default_boundary") or "quarantine"
