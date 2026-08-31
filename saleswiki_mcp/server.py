"""MCP stdio server: a thin wrapper over the permissioned core service.

Identity is resolved server-side from the session environment
(SALESWIKI_DEMO_ACTOR); the client never chooses its role. The SDK import is
lazy so the pure tool handlers (build_tools) remain importable and testable
without the `mcp` package installed.

Every tool handler returns the full envelope dict: rendered Markdown under
"text" plus machine-readable semantics (access / status / reason /
proposal_id). The MCP layer sends the text as the content block and the rest
as structuredContent, so clients read decision semantics as data instead of
re-parsing the prose — a wording change can never flip a client's
interpretation.
"""

from __future__ import annotations

import functools
import inspect
import os
from pathlib import Path
from typing import Callable

from . import config, vault_guard
from .identity import FixtureIdentityProvider
from .service import CompanyBriefService, build_default_service

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT = ROOT / "demo" / "permissioned"
DEFAULT_RUNTIME = ROOT / "demo" / "runtime"


def build_tools(service: CompanyBriefService, actor) -> dict[str, Callable]:
    """Return the role-bound tool handlers as plain callables (each -> envelope dict)."""

    def company_brief(company: str) -> dict:
        return service.company_brief(actor, company)

    def company_search(query: str) -> dict:
        return service.company_search(actor, query)

    def entity_graph(
        entity: str,
        entity_type: str = "company",
        depth: int = 1,
        include: list[str] | None = None,
    ) -> dict:
        return service.entity_graph(
            actor,
            entity=entity,
            entity_type=entity_type,
            depth=depth,
            include=include,
        )

    def dashboard(scope: str = "") -> dict:
        return service.dashboard(actor)

    def guided_answer(intent: str, company: str) -> dict:
        return service.guided_answer(actor, intent, company)

    def flag_stale_or_wrong(target: str, note: str) -> dict:
        proposal_id = service.flag_stale_or_wrong(actor, target, note)
        return {
            "text": f"Captured {proposal_id} (status: draft). It will be reviewed; production is unchanged.",
            "status": "draft", "proposal_id": proposal_id,
        }

    def deal_risk(company: str = "") -> dict:
        return service.deal_risk(actor, company or None)

    def call_prep(company: str) -> dict:
        return service.call_prep(actor, company)

    def lead_priority(company: str = "") -> dict:
        return service.lead_priority(actor, company or None)

    def event_brief(event: str) -> dict:
        return service.event_brief(actor, event)

    def campaign_brief(campaign: str) -> dict:
        return service.campaign_brief(actor, campaign)

    def content_opportunities(scope: str = "") -> dict:
        return service.content_opportunities(actor)

    def my_day(scope: str = "") -> dict:
        return service.my_day(actor)

    def pipeline_risk_digest(scope: str = "") -> dict:
        return service.pipeline_risk_digest(actor)

    def review_queue(scope: str = "") -> dict:
        return service.review_queue(actor)

    def get_proposal(proposal_id: str) -> dict:
        result = service.get_proposal(actor, proposal_id)
        if result["status"] == "blocked":
            text = f"Cannot view {proposal_id}: your role may not review proposals."
        elif result["status"] == "not-found":
            text = f"Proposal {proposal_id} was not found."
        else:
            text = f"Proposal {proposal_id}: status {result['status']}; details: {result['proposal']}"
        return {"text": text, **result}

    def reject_proposal(proposal_id: str, reason: str) -> dict:
        result = service.reject_proposal(actor, proposal_id, reason)
        status = result["status"]
        if status == "rejected":
            text = f"Proposal {proposal_id} rejected. Recorded append-only; production is unchanged and the worker will not apply it."
        elif status == "blocked":
            text = f"Cannot reject {proposal_id}: your role may not decide proposals."
        elif status == "not-found":
            text = f"Proposal {proposal_id} was not found."
        else:
            text = f"Proposal {proposal_id} is already {status}; nothing to do."
        return {"text": text, **result}

    def request_redaction_review(target: str, reason: str) -> dict:
        proposal_id = service.request_redaction_review(actor, target, reason)
        return {
            "text": f"Captured {proposal_id} (status: draft). An approver must approve it; the worker then applies it. Production is unchanged.",
            "status": "draft", "proposal_id": proposal_id,
        }

    def request_access(target: str, reason: str) -> dict:
        proposal_id = service.request_access(actor, target, reason)
        return {
            "text": f"Captured {proposal_id} (status: draft) — access request. An approver (curator/HoS/admin) can approve it to grant scoped, time-boxed access.",
            "status": "draft", "proposal_id": proposal_id,
        }

    def ingest_resource(target: str, note: str) -> dict:
        proposal_id = service.ingest_resource(actor, target, note)
        return {
            "text": f"Captured {proposal_id} (status: draft). The import summary is awaiting review; production is unchanged.",
            "status": "draft", "proposal_id": proposal_id,
        }

    def revoke_proposal(proposal_id: str, reason: str) -> dict:
        result = service.revoke_proposal(actor, proposal_id, reason)
        status = result["status"]
        if status == "revoked":
            text = f"Grant for {proposal_id} revoked. The requester loses the granted access immediately."
        elif status == "blocked":
            text = f"Cannot revoke {proposal_id}: your role may not decide proposals."
        elif status == "not-found":
            text = f"Proposal {proposal_id} was not found."
        else:
            text = f"Proposal {proposal_id} is {status}; not an active grant."
        return {"text": text, **result}

    def approve_proposal(proposal_id: str, ttl_days: int | None = None) -> dict:
        # Validate the optional TTL here so a bad client value can never approve
        # with a surprise expiry; None keeps the governance default (30 days).
        if ttl_days is not None and (isinstance(ttl_days, bool) or not isinstance(ttl_days, int) or ttl_days < 1):
            return {
                "text": "Invalid ttl_days: pass a positive integer number of days, or omit it for the default grant TTL.",
                "status": "invalid", "reason": "invalid ttl_days", "proposal_id": proposal_id,
            }
        result = service.approve_proposal(actor, proposal_id, ttl_days=ttl_days)
        status = result["status"]
        # Governance signals a no-op re-decision with reason 'not in draft' while
        # echoing the CURRENT status (which may itself be 'approved'), so the
        # no-op must be phrased before the fresh-approval branch. The envelope
        # carries the same marker, so clients classify by data, not phrasing.
        if result.get("reason") == "not in draft":
            text = (f"No change: proposal {proposal_id} is already in status '{status}'; "
                    f"nothing was approved and no new grant was issued.")
        elif status == "approved":
            text = f"Proposal {proposal_id} approved. The single-writer worker will apply it; production is unchanged until then."
        elif status == "blocked":
            text = f"Cannot approve {proposal_id}: your role may not approve proposals."
        elif status == "not-found":
            text = f"Proposal {proposal_id} was not found."
        else:
            text = f"Proposal {proposal_id} is {status}; nothing to do."
        return {"text": text, **result}

    return {
        "saleswiki.company_brief": company_brief,
        "saleswiki.company_search": company_search,
        "saleswiki.entity_graph": entity_graph,
        "saleswiki.dashboard": dashboard,
        "saleswiki.guided_answer": guided_answer,
        "saleswiki.flag_stale_or_wrong": flag_stale_or_wrong,
        "saleswiki.deal_risk": deal_risk,
        "saleswiki.call_prep": call_prep,
        "saleswiki.lead_priority": lead_priority,
        "saleswiki.event_brief": event_brief,
        "saleswiki.campaign_brief": campaign_brief,
        "saleswiki.content_opportunities": content_opportunities,
        "saleswiki.my_day": my_day,
        "saleswiki.pipeline_risk_digest": pipeline_risk_digest,
        "saleswiki.request_redaction_review": request_redaction_review,
        "saleswiki.request_access": request_access,
        "saleswiki.ingest_resource": ingest_resource,
        "saleswiki.approve_proposal": approve_proposal,
        "saleswiki.revoke_proposal": revoke_proposal,
        "saleswiki.review_queue": review_queue,
        "saleswiki.get_proposal": get_proposal,
        "saleswiki.reject_proposal": reject_proposal,
    }


TOOL_DESCRIPTIONS = {
    "saleswiki.company_brief": "Role-aware company brief: conclusion, summary, authorized detail, restricted notes, sources and next action.",
    "saleswiki.company_search": "Role-aware exact and substring company finder. Returns only accessible company labels and stable IDs; it never returns hidden match counts or card content.",
    "saleswiki.entity_graph": "Role-aware, layout-neutral company knowledge graph. Returns authorized nodes, relationships and evidence as the saleswiki.graph-view v1 contract; v1 supports company roots at depth 1.",
    "saleswiki.dashboard": "Role-aware dashboard read model. Returns only policy-filtered risk history, readiness coverage and dated source signals.",
    "saleswiki.guided_answer": "Role-aware guided assistant. Selects one allowlisted cited answer for the current company; it does not accept free-form prompts or client-selected tools.",
    "saleswiki.flag_stale_or_wrong": "Flag a card as stale or wrong. Creates an append-only proposal; never mutates production.",
    "saleswiki.deal_risk": "Role-aware deal risk: risk and next action for deals you may see. Pass a company name, or leave empty for all accessible deals; restricted roles get an aggregated count only.",
    "saleswiki.call_prep": "Role-aware call prep: a sanitized pre-call summary with an opaque handle to the raw transcript; unauthorized roles get a sanitized 'sales feedback only' note.",
    "saleswiki.lead_priority": "Role-aware lead priority: ranked MQL leads with score band, why-now and next action; the contact stays an opaque handle and linked deal risk is added only for authorized roles. Pass a company name or leave empty for all leads.",
    "saleswiki.event_brief": "Role-aware event brief: public target accounts for an event, with per-account deal context added only for roles that may read that deal; marketing gets the brief without restricted deal detail.",
    "saleswiki.campaign_brief": "Role-aware campaign brief: public target accounts and content angle for all roles; per-account deal context only for roles that may read that deal; marketing gets no restricted deal detail.",
    "saleswiki.content_opportunities": "Broad marketing content opportunities: known pain points with a content angle and a suggested asset. Public-safe; shared with sales and marketing.",
    "saleswiki.my_day": "Role-aware personal daily digest: the actor's lead priorities and at-risk deals, access-filtered (marketing gets leads but no deal detail).",
    "saleswiki.pipeline_risk_digest": "Role-aware pipeline risk digest: deals at risk the actor may read plus pending-proposal count; HoS/RevOps see all, a sales owner only their own, marketing only an aggregate.",
    "saleswiki.request_redaction_review": "Request a redaction review for a card. Creates an append-only draft proposal; an approver approves and the single-writer worker applies it. Never mutates production directly.",
    "saleswiki.request_access": "Request access to a restricted source. Creates an append-only draft proposal; an approver can approve it to grant scoped, time-boxed read access.",
    "saleswiki.ingest_resource": "Submit a concise import summary for a known card. It creates an append-only review proposal and never writes an entity card.",
    "saleswiki.approve_proposal": "Approve a draft proposal (approver roles only). Append-only; the single-writer worker applies it later. Production is unchanged at approval time. For a request_access proposal, optional ttl_days sets the grant lifetime (default 30 days).",
    "saleswiki.revoke_proposal": "Revoke an approved access grant (approver roles only). Append-only; the requester loses the granted access immediately.",
    "saleswiki.review_queue": "Reviewer inbox (curator/HoS/RevOps/admin): proposals awaiting a decision. Read-only and append-only; never mutates production.",
    "saleswiki.get_proposal": "Full state of one proposal, for reviewer roles.",
    "saleswiki.reject_proposal": "Reject a draft proposal (approver roles only). Append-only; a rejected proposal is never applied by the worker.",
}


def build_default_runtime() -> tuple[CompanyBriefService, object]:
    """Build the service and resolve the actor from the server environment."""
    vault_root = Path(os.environ.get("SALESWIKI_VAULT_ROOT", str(DEFAULT_VAULT)))
    runtime = Path(os.environ.get("SALESWIKI_RUNTIME_DIR", str(DEFAULT_RUNTIME)))
    # Fixture identity is not authentication (ADR-0013): fail closed rather than
    # serve a production-shaped vault under a fixture actor until SSO lands.
    vault_guard.require_demo_vault(vault_root, context="MCP gateway (fixture identity)")
    service = build_default_service(
        vault_root=vault_root,
        audit_path=runtime / "audit.jsonl",
        proposal_path=runtime / "proposals.jsonl",
    )
    actor = FixtureIdentityProvider.from_env(config.identity_config()).resolve()
    return service, actor


def _as_tool_result(fn: Callable) -> Callable:
    """Adapt an envelope-returning handler for FastMCP: the rendered text becomes
    the human-readable content block and every other envelope field rides in
    structuredContent, so MCP clients read semantics (access / status / reason /
    proposal_id) as data instead of re-parsing the prose."""
    from mcp import types

    @functools.wraps(fn)
    def tool(**kwargs):
        envelope = fn(**kwargs)
        structured = {k: v for k, v in envelope.items() if k != "text"}
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=str(envelope.get("text", "")))],
            structuredContent=structured or None,
        )

    # FastMCP derives the input schema from the signature; keep the original
    # parameters but drop the dict return annotation so no output schema is
    # inferred and the CallToolResult above passes through untouched.
    tool.__signature__ = inspect.signature(fn).replace(return_annotation=inspect.Signature.empty)
    tool.__annotations__ = {k: v for k, v in fn.__annotations__.items() if k != "return"}
    return tool


def create_server(service: CompanyBriefService, actor):
    """Wire the role-bound tools into a FastMCP stdio server."""
    from mcp.server.fastmcp import FastMCP

    app = FastMCP("saleswiki")
    tools = build_tools(service, actor)
    for name, description in TOOL_DESCRIPTIONS.items():
        app.add_tool(_as_tool_result(tools[name]), name=name, description=description)
    return app


def main() -> int:
    service, actor = build_default_runtime()
    app = create_server(service, actor)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
