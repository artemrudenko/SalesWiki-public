"""Approval key resolution must never hand back a weak key (security review #8).

resolve_key returned whatever bytes the per-runtime .approval_key file held,
including b"" for a 0-byte file (a pre-created stub, a truncated copy, or a crash
in the non-atomic create window). Signing under an empty/short key is forgeable —
the exact protection the module exists to provide. A too-short key must be
regenerated, and a valid key returned unchanged.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp import signing  # noqa: E402


class ResolveKeyStrength(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = Path(tempfile.mkdtemp(prefix="approval-key-"))
        # The env var short-circuits the file path; ensure the file path is tested.
        self._saved_env = os.environ.pop(signing.ENV_KEY, None)

    def tearDown(self) -> None:
        if self._saved_env is not None:
            os.environ[signing.ENV_KEY] = self._saved_env

    def _key_file(self) -> Path:
        return self.runtime / signing.KEY_FILE

    def test_empty_key_file_is_not_trusted(self) -> None:
        self._key_file().write_bytes(b"")
        key = signing.resolve_key(self.runtime)
        self.assertGreaterEqual(len(key), 16, "a 0-byte key file must not yield an empty key")

    def test_short_key_file_is_regenerated(self) -> None:
        self._key_file().write_bytes(b"abc")
        key = signing.resolve_key(self.runtime)
        self.assertGreaterEqual(len(key), 16)
        # The weak stub must have been replaced on disk, not just in memory.
        self.assertGreaterEqual(len(self._key_file().read_bytes()), 16)

    def test_valid_key_file_is_returned_unchanged(self) -> None:
        original = os.urandom(32)
        self._key_file().write_bytes(original)
        self.assertEqual(signing.resolve_key(self.runtime), original)

    def test_first_use_creates_a_strong_stable_key(self) -> None:
        key = signing.resolve_key(self.runtime)
        self.assertGreaterEqual(len(key), 16)
        self.assertEqual(signing.resolve_key(self.runtime), key, "key must be stable across calls")


if __name__ == "__main__":
    unittest.main()
