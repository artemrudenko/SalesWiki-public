"""Signed audit checkpoints protect an already-recorded log prefix."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from saleswiki_mcp.audit import AuditAnchorError, AuditSink, advance_anchor, create_anchor, verify_anchor  # noqa: E402


class AuditAnchorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="audit-anchor-"))
        self.audit = self.tmp / "runtime" / "audit.jsonl"
        self.audit.parent.mkdir()
        self.anchor = self.tmp / "protected" / "audit.anchor.json"
        self.key = b"test-only-anchor-key"
        self.sink = AuditSink(self.audit)
        for number in range(3):
            self.sink.record({"tool": "company_brief", "number": number})

    def test_anchor_allows_new_events_but_rejects_tail_truncation(self) -> None:
        checkpoint = create_anchor(self.audit, self.anchor, self.key)
        self.assertEqual(checkpoint["count"], 3)
        self.sink.record({"tool": "deal_risk", "number": 3})
        self.assertTrue(verify_anchor(self.audit, self.anchor, self.key))
        kept = self.audit.read_text(encoding="utf-8").splitlines()[:2]
        self.audit.write_text("\n".join(kept) + "\n", encoding="utf-8")
        self.assertFalse(verify_anchor(self.audit, self.anchor, self.key))

    def test_signature_rejects_a_modified_checkpoint(self) -> None:
        create_anchor(self.audit, self.anchor, self.key)
        content = self.anchor.read_text(encoding="utf-8").replace('"count": 3', '"count": 2')
        self.anchor.write_text(content, encoding="utf-8")
        self.assertFalse(verify_anchor(self.audit, self.anchor, self.key))

    def test_advance_requires_the_existing_checkpoint_to_verify(self) -> None:
        create_anchor(self.audit, self.anchor, self.key)
        self.sink.record({"tool": "deal_risk", "number": 3})
        checkpoint = advance_anchor(self.audit, self.anchor, self.key)
        self.assertEqual(checkpoint["count"], 4)
        with self.assertRaises(AuditAnchorError):
            create_anchor(self.audit, self.anchor, self.key)


if __name__ == "__main__":
    unittest.main()
