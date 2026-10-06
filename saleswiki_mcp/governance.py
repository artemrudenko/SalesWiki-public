"""Proposal capture, approval and review (the write-governance side).

Split out of the former god-class so reads and governance have separate
responsibilities; the read service composes this and delegates, keeping the
public tool API unchanged. All transitions are append-only and never mutate a
card - the single-writer worker is the only writer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from . import signing
from .audit import AuditSink
from .policy import PolicyEvaluator
from .proposals import ProposalStore, content_hash, payload_hash
from .retrieval import Retriever

# Default lifetime of an access grant issued by approving a request_access proposal.
DEFAULT_GRANT_TTL_DAYS = 30
# Upper bound on an approver-supplied ttl. Caps the grant horizon and, crucially,
# keeps `days` well inside timedelta's ~1e9-day limit so an absurd ttl cannot
# raise OverflowError (nor be silently turned into an eternal grant).
MAX_GRANT_TTL_DAYS = 3650  # ten years


def _sanitize_note(note: str) -> str:
    """Collapse a free-text proposal note to a single safe line before it can be
    written verbatim into a card body. A multi-line note would otherwise let a
    requester inject arbitrary Markdown — including new `## ` headings that the
    section-based extractors could later serve as vault truth. Newlines become
    spaces, a leading `#` is stripped, and the note is length-capped."""
    flat = " ".join(note.split())
    return flat.lstrip("#").strip()[:500]


def _add_days(iso: str, days: int) -> str | None:
    """`iso` plus `days`, or None when `iso` is not a parseable timestamp (test
    stubs use now=lambda: "t"). Returning None instead of raising lets a grant be
    issued without an expiry under a stub clock — mirroring the proposal store,
    where an unparseable *now* only disables time filtering (an unparseable
    stored expiry, by contrast, fails closed there)."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (dt + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


class GovernanceService:
    def __init__(
        self,
        retriever: Retriever,
        policy: PolicyEvaluator,
        audit: AuditSink,
        proposals: ProposalStore,
        now: Callable[[], str],
        approval_key: bytes | None = None,
    ) -> None:
        self._retriever = retriever
        self._policy = policy
        self._audit = audit
        self._proposals = proposals
        self._now = now
        self._approval_key = approval_key

    def _log_digest(self, actor, tool: str, resource: str) -> None:
        self._audit.record(
            {"timestamp": self._now(), "actor": actor.id, "role": actor.role,
             "tool": tool, "resource": resource, "decision": "allow"}
        )

    # -- propose -----------------------------------------------------------
    def flag_stale_or_wrong(self, actor, target: str, note: str) -> str:
        return self._capture_proposal(actor, "flag_stale_or_wrong", target, note)

    def request_redaction_review(self, actor, target: str, reason: str) -> str:
        return self._capture_proposal(actor, "request_redaction_review", target, reason)

    def request_access(self, actor, target: str, reason: str) -> str:
        """Ask a reviewer to grant access to a restricted source. Captured like any
        proposal so it lands in the review queue; the access grant itself happens
        out-of-band (this MVP records an audited request, not an automatic grant)."""
        return self._capture_proposal(actor, "request_access", target, reason)

    def ingest_resource(self, actor, target: str, note: str) -> str:
        """Propose ingesting an external resource (e.g. a connected Drive file) into
        a card. Captured like any proposal: it never writes the card itself, it just
        queues a 'create/update card from this source' task for reviewer approval;
        the worker then appends it to the target card's Review Needed section."""
        return self._capture_proposal(actor, "ingest_resource", target, note)

    def _capture_proposal(self, actor, ptype: str, target: str, note: str) -> str:
        """Append-only capture of any proposal type, with payload and base hashes
        so the single-writer worker can validate integrity before applying.

        The target is canonicalized to the resolved card's entity id so an access
        grant keys on the same id the policy checks reads against — a raw display
        name would be approved yet silently never match (dangling grant). The note
        is sanitized to a single line so it cannot inject Markdown into the card.
        """
        note = _sanitize_note(note)
        card = self._retriever.find(target)
        canonical_target = card.entity_id if card is not None and card.entity_id else target
        base_hash = content_hash(card.body) if card is not None else ""
        proposal_id = self._proposals.append(
            {
                "type": ptype,
                "status": "draft",
                "requester": actor.id,
                "role": actor.role,
                "target": canonical_target,
                "note": note,
                "payload_hash": payload_hash(ptype, canonical_target, note),
                "base_hash": base_hash,
                "base_path": card.rel_path if card is not None else "",
                "created": self._now(),
            }
        )
        self._audit.record(
            {
                "timestamp": self._now(),
                "actor": actor.id,
                "role": actor.role,
                "tool": ptype,
                "resource": canonical_target,
                "decision": "proposal",
                "proposal_id": proposal_id,
            }
        )
        return proposal_id

    # -- approve / reject --------------------------------------------------
    def approve_proposal(self, actor, proposal_id: str, ttl_days: int | None = None) -> dict:
        """Approve a draft proposal (approver roles only); append-only, no card
        mutation. The worker applies an approved proposal separately. For a
        request_access proposal the approval also stamps a grant expiry so the
        access overlay is time-boxed."""
        decision = self._policy.can_approve(actor)
        state = self._proposals.state(proposal_id)
        # Compute the grant expiry BEFORE the audit allow-event and the status
        # append: nothing between those two writes may raise, or the log would
        # show an approval that never landed (stuck draft + lying audit trail).
        # Under an unparseable now() stub the grant simply carries no expiry.
        grant_expires: str | None = None
        if state.get("type") == "request_access":
            days = DEFAULT_GRANT_TTL_DAYS if ttl_days is None else ttl_days
            days = max(1, min(days, MAX_GRANT_TTL_DAYS))  # clamp: no overflow, no eternal grant
            grant_expires = _add_days(self._now(), days)
        self._audit.record(
            {"timestamp": self._now(), "actor": actor.id, "role": actor.role,
             "tool": "approve_proposal", "resource": proposal_id,
             "decision": decision.effect, "reason": decision.reason}
        )
        if decision.effect != "allow":
            return {"proposal_id": proposal_id, "status": "blocked", "reason": decision.reason}
        if not state:
            return {"proposal_id": proposal_id, "status": "not-found"}
        if state.get("status") != "draft":
            return {"proposal_id": proposal_id, "status": state.get("status"), "reason": "not in draft"}
        record = {"event": "approval_decision", "status": "approved", "approver": actor.id,
                  "approver_role": actor.role, "approved": self._now()}
        if grant_expires is not None:
            record["grant_expires"] = grant_expires
        # Sign the approval so the worker and grant overlay trust only approvals a
        # key holder issued — a forged `approved` line has no valid signature. The
        # requester is signed explicitly (it is not in payload_hash) so the grant
        # cannot be re-pointed to another user after signing.
        if self._approval_key is not None:
            signed = {"proposal_id": proposal_id, "payload_hash": state.get("payload_hash", ""),
                      "requester": state.get("requester", ""), **record}
            record[signing.SIG_FIELD] = signing.sign(self._approval_key, signed)
        self._proposals.append_status(proposal_id, record)
        return {"proposal_id": proposal_id, "status": "approved"}

    def revoke_proposal(self, actor, proposal_id: str, reason: str) -> dict:
        """Revoke an approved (or worker-applied) access grant (approver roles
        only). Append-only; the access overlay drops the grant as soon as the
        'revoked' status is recorded."""
        decision = self._policy.can_approve(actor)
        state = self._proposals.state(proposal_id)
        self._audit.record(
            {"timestamp": self._now(), "actor": actor.id, "role": actor.role,
             "tool": "revoke_proposal", "resource": proposal_id,
             "decision": decision.effect, "reason": decision.reason}
        )
        if decision.effect != "allow":
            return {"proposal_id": proposal_id, "status": "blocked", "reason": decision.reason}
        if not state:
            return {"proposal_id": proposal_id, "status": "not-found"}
        if state.get("status") not in ProposalStore.GRANT_ACTIVE_STATUSES:
            return {"proposal_id": proposal_id, "status": state.get("status"), "reason": "not an active grant"}
        self._proposals.append_status(
            proposal_id,
            {"event": "revoke_decision", "status": "revoked", "revoker": actor.id,
             "reason": reason, "revoked": self._now()},
        )
        return {"proposal_id": proposal_id, "status": "revoked"}

    def reject_proposal(self, actor, proposal_id: str, reason: str) -> dict:
        """Reject a draft proposal (approver-only). Append-only; a rejected
        proposal is never applied by the worker."""
        decision = self._policy.can_approve(actor)
        state = self._proposals.state(proposal_id)
        self._audit.record(
            {"timestamp": self._now(), "actor": actor.id, "role": actor.role,
             "tool": "reject_proposal", "resource": proposal_id,
             "decision": decision.effect, "reason": decision.reason}
        )
        if decision.effect != "allow":
            return {"proposal_id": proposal_id, "status": "blocked", "reason": decision.reason}
        if not state:
            return {"proposal_id": proposal_id, "status": "not-found"}
        if state.get("status") != "draft":
            return {"proposal_id": proposal_id, "status": state.get("status"), "reason": "not in draft"}
        self._proposals.append_status(
            proposal_id,
            {"event": "review_decision", "status": "rejected", "reviewer": actor.id,
             "reason": reason, "rejected": self._now()},
        )
        return {"proposal_id": proposal_id, "status": "rejected"}

    # -- review ------------------------------------------------------------
    def proposal_state(self, proposal_id: str) -> dict:
        return self._proposals.state(proposal_id)

    def review_queue(self, actor) -> dict:
        """Reviewer inbox: proposals awaiting a decision (draft/approved). Visible
        to reviewer roles; read-only and append-only."""
        decision = self._policy.can_review(actor)
        can_decide = self._policy.can_approve(actor).effect == "allow"
        self._log_digest(actor, "review_queue", "(review-queue)")
        if decision.effect != "allow":
            return {"access": "blocked", "can_decide": False, "text": f"# Review Queue\n\n**Blocked:** {decision.reason}.\n", "items": []}
        pending = [s for s in self._proposals.states().values() if s.get("status") in ("draft", "approved")]
        lines = ["# Review Queue", "", f"**Conclusion:** {len(pending)} proposal(s) awaiting a decision.", ""]
        for s in pending:
            lines += [
                f"## {s.get('proposal_id')} ({s.get('status')})",
                f"- Type: {s.get('type')}",
                f"- Target: {s.get('target')}",
                f"- Requester: {s.get('requester')} ({s.get('role')})",
                f"- Note: {s.get('note')}",
                "",
            ]
        return {"access": "allowed", "can_decide": can_decide, "text": "\n".join(lines) + "\n", "items": pending}

    def get_proposal(self, actor, proposal_id: str) -> dict:
        """Full state of one proposal, for reviewer roles."""
        decision = self._policy.can_review(actor)
        self._log_digest(actor, "get_proposal", proposal_id)
        if decision.effect != "allow":
            return {"status": "blocked", "reason": decision.reason}
        state = self._proposals.state(proposal_id)
        if not state:
            return {"status": "not-found", "proposal_id": proposal_id}
        return {"status": state.get("status"), "proposal": state}
