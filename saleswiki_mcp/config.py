"""Load the permissioned contracts from schemas/."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def access_policy() -> dict:
    return _load("access-policy.json")


def boundary_registry() -> dict:
    return _load("boundary-registry.json")


def identity_config() -> dict:
    return _load("identity-provider.json")


def field_extraction() -> dict:
    return _load("field-extraction.json")
