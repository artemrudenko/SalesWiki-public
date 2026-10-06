"""RBAC + ABAC policy evaluation. The gateway enforces this before any output.

Decision effects:
- allow:  the actor may see the full card content
- handle: personal-data shown only as an opaque restricted handle
- block:  the actor may not see the card at all
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Resource:
    entity_id: str
    boundary: str
    owner: str = ""
    team: str = ""
    company: str = ""


@dataclass(frozen=True)
class Decision:
    effect: str  # "allow" | "handle" | "block"
    reason: str


class PolicyEvaluator:
    def __init__(
        self,
        policy: dict,
        grants_provider: Callable[[], set[tuple[str, str, str]]] | None = None,
    ) -> None:
        self._roles = {r["id"]: r for r in policy.get("roles", [])}
        self._rules = policy.get("rules", {})
        # Live source of active access grants as {(actor_id, target_id, boundary)}
        # triples; injected so an approval takes effect without rebuilding the policy.
        self._grants_provider = grants_provider

    def can_read(self, actor, resource: Resource) -> Decision:
        decision = self._base_decision(actor, resource)
        # An explicit, approved grant is an additive override: it can only upgrade a
        # blocked/handle restricted read to allow for the granted requester, company
        # and boundary. It never widens anything else or reduces access.
        if decision.effect in ("block", "handle") and self._is_granted(actor, resource):
            return Decision("allow", "active access grant")
        return decision

    def _is_granted(self, actor, resource: Resource) -> bool:
        if self._grants_provider is None:
            return False
        grants = self._grants_provider()
        actor_id = getattr(actor, "id", "")
        boundary = resource.boundary
        return (
            (actor_id, resource.company, boundary) in grants
            or (actor_id, resource.entity_id, boundary) in grants
        )

    def _base_decision(self, actor, resource: Resource) -> Decision:
        role = self._roles.get(actor.role)
        if role is None:
            return Decision("block", f"unknown role {actor.role}")
        allowed = role.get("boundaries", [])

        if resource.boundary == "personal-data":
            if resource.boundary in allowed:
                return Decision("allow", "authorized for personal-data")
            behavior = self._rules.get("personal_data_unauthorized_behavior", "opaque-handle")
            if behavior == "opaque-handle":
                return Decision("handle", "personal-data restricted to opaque handle")
            return Decision("block", "personal-data restricted")

        if resource.boundary not in allowed:
            return Decision("block", f"{actor.role} cannot read {resource.boundary}")

        constraint = role.get("attribute_constraints", {}).get(resource.boundary)
        if constraint == "owned_or_team":
            if self._matches_ownership(actor, resource, include_team=True):
                return Decision("allow", "ownership/team match")
            return Decision("block", f"{actor.role} not on the team for this {resource.boundary} record")
        if constraint == "assigned":
            # An SDR only sees records explicitly assigned to them (owner or owned
            # account), never the whole team's - strictly narrower than owned_or_team.
            if self._matches_ownership(actor, resource, include_team=False):
                return Decision("allow", "assigned to actor")
            return Decision("block", f"{actor.role} not assigned to this {resource.boundary} record")
        if constraint is not None:
            # A constraint was configured but is not one this code implements (a
            # typo, or a future/renamed narrowing). Deny on doubt: the operator
            # meant to narrow the boundary, so an unrecognized value must fail
            # closed, never fall through to granting the whole boundary.
            return Decision("block", f"{actor.role} has an unrecognized constraint on {resource.boundary}")

        return Decision("allow", "role grants boundary")

    def can_approve(self, actor) -> Decision:
        """Only approver roles (e.g. curator/HoS/admin) may approve/reject proposals."""
        approvers = self._rules.get("approver_roles", [])
        if actor.role in approvers:
            return Decision("allow", f"{actor.role} may approve proposals")
        return Decision("block", f"{actor.role} may not approve proposals")

    def can_review(self, actor) -> Decision:
        """Reviewer roles (e.g. curator/HoS/RevOps/admin) may inspect the queue.
        Broader than approvers: RevOps can inspect but not decide.
        """
        reviewers = self._rules.get("reviewer_roles", [])
        if actor.role in reviewers:
            return Decision("allow", f"{actor.role} may review proposals")
        return Decision("block", f"{actor.role} may not review proposals")

    @staticmethod
    def _matches_ownership(actor, resource: Resource, include_team: bool) -> bool:
        if resource.owner and resource.owner == actor.id:
            return True
        if include_team and resource.team and resource.team == actor.team:
            return True
        if resource.company and resource.company in actor.owns:
            return True
        return False
