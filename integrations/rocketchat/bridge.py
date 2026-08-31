#!/usr/bin/env python3
"""Rocket.Chat entry point and backwards-compatible public facade.

The implementation is split by responsibility across private bridge modules.
Keeping this module thin preserves the documented command and the existing
import surface used by tests and local integrations.
"""

from __future__ import annotations

import subprocess
import sys
import urllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from _bridge_app import *  # noqa: F401,F403
from _bridge_client import RocketChat
from _bridge_common import *  # noqa: F401,F403
from _bridge_common import _child_env
from _bridge_wiki import Wiki


if __name__ == "__main__":
    raise SystemExit(main())
