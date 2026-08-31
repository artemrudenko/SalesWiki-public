"""Grant-overlay tamper regression (security review 2026-07-04, critical cluster).

The live access-grant overlay authorizes reads on `requester`, `target` and
`type`, but the approval signature originally bound none of them directly on the
read path (only `payload_hash`, and `active_grants` never re-derived it). So an
actor with only proposal-store *append* access — no signing key, the exact
adversary `signing.py` exists to defend — could hijack a
validly signed grant onto a different requester/company/type, or silently
restore a revoked grant by corrupting the revoke line.

Each test appends a tampered line to a store that already holds ONE legitimately
signed grant, then asserts the read stays blocked. The single-writer worker
already cross-checks these (worker.py re-derives payload_hash); these tests pin
the same defenses onto the read overlay.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.proposals import ProposalStore  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

BLUEPEAK = "demo-company-bluepeak-energy"
ATLAS = "demo-company-atlas-foods"


class GrantTamper(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="grant-tamper-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.audit = self.tmp / "audit.jsonl"
        self.proposals = self.tmp / "proposals.jsonl"
        self.runtime = self.tmp / "runtime"
        # build_default_service resolves a real per-runtime signing key, so the
        # grant overlay verifies signatures exactly as in production.
        self.svc = build_default_service(
            self.vault, self.audit, self.proposals, now=lambda: "2026-06-14T00:00:00Z"
        )
        self.store = ProposalStore(self.proposals)

    def who(self, actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def deal_access(self, actor_id: str, company: str) -> str:
        return self.svc.deal_risk(self.who(actor_id), company)["access"]

    def _signed_bluepeak_grant(self) -> str:
        """A viewer's legitimately signed, approved access grant on BluePeak."""
        pid = self.svc.request_access(self.who("demo-broad-viewer"), BLUEPEAK, "need it")
        self.svc.approve_proposal(self.who("demo-marina-curator"), pid)
        self.assertEqual(
            self.deal_access("demo-broad-viewer", "BluePeak Energy"),
            "allowed",
            "precondition: the legit signed grant must unlock the read",
        )
        return pid

    def test_target_swap_on_signed_grant_is_rejected(self) -> None:
        """Redirecting a signed grant to another company must not unlock it: the
        target lives inside the signed payload_hash, so the read overlay must
        re-derive and reject the mismatch (mirroring the worker)."""
        pid = self._signed_bluepeak_grant()
        self.assertEqual(self.deal_access("demo-broad-viewer", "Atlas Foods"), "blocked")
        # Attacker (append-only, no key) re-points the grant to Atlas.
        self.store.append_status(pid, {"target": ATLAS})
        self.assertEqual(
            self.deal_access("demo-broad-viewer", "Atlas Foods"),
            "blocked",
            "a post-signing target swap must not redirect the grant",
        )

    def test_requester_swap_on_signed_grant_is_rejected(self) -> None:
        """Re-pointing a signed grant to a different requester must not unlock it:
        requester is not covered by payload_hash, so it must be a signed field."""
        pid = self._signed_bluepeak_grant()
        self.assertEqual(self.deal_access("demo-nina-marketing", "BluePeak Energy"), "blocked")
        # Attacker hands the grant to marketing (zero sales-confidential access).
        self.store.append_status(pid, {"requester": "demo-nina-marketing"})
        self.assertEqual(
            self.deal_access("demo-nina-marketing", "BluePeak Energy"),
            "blocked",
            "a post-signing requester swap must not hand the grant to another user",
        )

    def test_type_flip_on_signed_flag_yields_no_grant(self) -> None:
        """A signed non-access approval (flag_stale) flipped to request_access must
        not become a grant: type is inside payload_hash, so re-derivation rejects
        it. (This variant also carries no grant_expires, so absent the guard it
        would be an eternal grant.)"""
        # A viewer's signed, approved flag_stale on BluePeak — no grant of any kind.
        pid = self.svc.flag_stale_or_wrong(self.who("demo-broad-viewer"), BLUEPEAK, "stale")
        self.svc.approve_proposal(self.who("demo-marina-curator"), pid)
        self.assertEqual(self.deal_access("demo-broad-viewer", "Atlas Foods"), "blocked")
        # Attacker flips it into a request_access grant on Atlas (requester unchanged).
        self.store.append_status(pid, {"type": "request_access", "target": ATLAS})
        self.assertEqual(
            self.deal_access("demo-broad-viewer", "Atlas Foods"),
            "blocked",
            "flipping a flag_stale approval to request_access must not forge a grant",
        )

    def test_corrupted_revoke_line_fails_closed(self) -> None:
        """A revoke record whose bytes are corrupted must not silently restore the
        grant. The grant log is security state; a line it cannot parse could be a
        tampered revoke, so grant derivation fails closed rather than reverting to
        the last-parseable (more permissive) approved state."""
        pid = self._signed_bluepeak_grant()
        out = self.svc.revoke_proposal(self.who("demo-marina-curator"), pid, "no longer needed")
        self.assertEqual(out["status"], "revoked")
        self.assertEqual(self.deal_access("demo-broad-viewer", "BluePeak Energy"), "blocked")
        # Corrupt the revoke line's bytes (a torn write on crash, or tampering by a
        # process with write access to the runtime dir) so it no longer parses.
        lines = self.proposals.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if '"status": "revoked"' in line:
                lines[i] = line[: len(line) // 2]  # truncated -> invalid JSON
        self.proposals.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertEqual(
            self.deal_access("demo-broad-viewer", "BluePeak Energy"),
            "blocked",
            "a corrupted revoke line must not restore the revoked grant",
        )


if __name__ == "__main__":
    unittest.main()
