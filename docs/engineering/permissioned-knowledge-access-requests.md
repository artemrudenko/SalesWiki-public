---
title: Permissioned Knowledge - Access Requests & Grants
tags:
  - process
  - architecture
  - governance
  - mcp
  - mvp
status: draft
updated: 2026-06-14
---

# Permissioned Knowledge - Access Requests & Grants

How a user asks for access to a restricted source, who reviews it, how they
receive it, and what "granting" actually means today versus in the SSO target
state. This complements [[permissioned-knowledge-overview]] (the map) and the
governance model in [[permissioned-knowledge-architecture]].

It exists because the chat bridge ([[../../integrations/rocketchat/README]]) and
every read tool surface a `request access` affordance for restricted data — so the
*grant* side must be designed, not left implicit.

## The request side (implemented)

`request_access` is a first-class proposal type, captured exactly like
`flag_stale_or_wrong` and `request_redaction_review`:

- `service.request_access(actor, target, reason)` → `governance.request_access`
  → `_capture_proposal(actor, "request_access", target, reason)`.
- It is append-only: it never mutates a card and never grants anything by itself.
- Any role may file one (asking is not privileged); the proposal records the
  requester id, role, target entity id, reason, and a payload/base hash.
- It lands in the review queue with `type: request_access`.

In the Rocket.Chat demo this is the `запросить доступ <причина>` command, filed
against the last-discussed company.

## The review side (implemented)

Who sees and decides is config-driven in `schemas/access-policy.json`:

| Capability | Roles | Enforced by |
| --- | --- | --- |
| See `review_queue` / `get_proposal` | `curator`, `hos`, `revops`, `admin` (`reviewer_roles`) | `policy.can_review` |
| `approve_proposal` / `reject_proposal` | `curator`, `hos`, `admin` (`approver_roles`) | `policy.can_approve` |

**How a reviewer receives the request — today it is pull-based**: a reviewer role
opens the queue (`review_queue`, or `очередь ревью` in chat). There is no push
notification yet. On approval, the single-writer worker appends an audited bullet
to the target card's *Review Needed* section ("Access requested: … requester … approved by …").

## The grant side (implemented v1 + roadmap)

**Implemented: approve = a live, scoped, time-boxed grant.**
`proposals.active_grants(now)` derives `{(requester, target, boundary)}` triples
from approved (non-revoked, non-expired) `request_access` proposals, and
`PolicyEvaluator` consults it as an **additive override**: it upgrades a
blocked/handle restricted read to `allow` only for that requester, that company
and that boundary — never widens anything else, never reduces access. It takes
effect the instant the approval is appended (no worker run, no role switch).

- **Scope:** per-company. `sales-confidential` for any approver; `personal-data`
  **only when an admin approved** (curator/HoS approvals never unlock personal-data).
- **Expiry:** each grant is time-boxed (default 30 days; `одобрить <id> [дней]`).
  `active_grants` drops expired grants.
- **Revocation:** `отозвать <id> <причина>` appends a `revoked` status; the overlay
  drops it immediately (counts only `approved`).
- **Notification:** filing a request posts a heads-up to approvers in the channel,
  and entering a reviewer role shows a pending-decision count.

Still roadmap — role-elevation grants (vs per-company), and push to *specific*
approver users (multi-user / SSO) rather than a single-channel notice. Those mean
changing one of the inputs the policy reads:

1. **Role elevation** — give the requester a role whose `boundaries` include the
   needed boundary (e.g. `employee-viewer` → `sales` adds `sales-confidential`).
   Coarse; affects every record in that boundary.
2. **ABAC assignment** — keep the role, but satisfy the `attribute_constraints`
   for one record: add the account to the requester's `owns`/`team` so
   `sales-confidential: assigned` / `owned_or_team` passes. Fine-grained,
   per-account — the right tool for "I need this one deal".
3. **personal-data exception** — only `admin` holds the `personal-data` boundary;
   `personal_data_default` is `deny`. A grant here should be rare, time-boxed and
   legal-aware, never a routine role bump.

### Where a grant is applied

- **Demo (fixture identity):** role is resolved from `schemas/identity-provider.json`
  (`providers.fixture.users[].role/team/owns`). A grant = editing that file.
  Caveat: in the chat demo the role is **self-asserted** via `роль:`, so the
  request→approve loop demonstrates governance *UX*, not enforcement — the demo
  user can already self-switch. The flow proves the model; SSO makes it binding.
- **Production (SSO target):** role comes from IdP group membership via
  `group_role_map` in `schemas/identity-provider.json`. A grant = changing the
  user's groups in the IdP (out-of-band, by an IdP/admin), or an ABAC assignment
  recorded in the vault roster. See [[permissioned-knowledge-sso-design]].

### Recommended target design

- Add a `grant_access` governance action available to `approver_roles` only, that
  records the grant decision (scope: role-bump vs account-assignment, expiry) in an
  append-only grants log — the policy reads it as an overlay, so grants are
  auditable, time-boxable and revocable without editing identity config by hand.
- Push, don't only pull: include the count of pending `request_access` items in the
  reviewer digests (`my_day` / `pipeline_risk_digest`) and, where a chat channel
  exists, notify a reviewer when a request is filed.
- Default to **ABAC assignment over role elevation** (least privilege); reserve
  `personal-data` grants for `admin` + explicit expiry.

## Status summary

| Piece | State |
| --- | --- |
| `request_access` proposal type (service + worker + tests) | ✅ implemented |
| Chat `запросить доступ` / `очередь ревью` | ✅ implemented (bridge) |
| Reviewer/approver roles (config) | ✅ existing policy |
| Approve = scoped grant (proposal-derived overlay, policy override) | ✅ implemented (per-company, per-boundary) |
| Chat `одобрить` / `отклонить` / `отозвать` (approver-only) | ✅ implemented (bridge) |
| Grant revocation (`revoked` status) | ✅ implemented |
| Time-boxed expiry (default 30d, `одобрить <id> [дней]`) | ✅ implemented |
| personal-data grant (admin approval only) | ✅ implemented |
| Reviewer notification (request heads-up + pending count on role entry) | ✅ implemented (bridge) |
| Role-elevation grants (vs per-company) | ⬜ design — v1 is per-company/boundary |
| Push to specific approver users (multi-user / SSO) | ⬜ design — single-channel notice today |
| Enforced grant binding under real identity | ⬜ requires SSO (role self-asserted in demo; grant itself is real + scoped) |
