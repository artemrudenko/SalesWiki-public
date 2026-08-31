"""Core company-brief service: ties identity, policy, retrieval, formatter, audit
and proposals into role-shaped, access-filtered answers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config, signing
from .audit import AuditSink
from .answer import Answer, Citation, Section, Table
from .dashboard import DashboardProjector
from .formatter import extract_section, field_value, find_handle, wikilink_targets
from .graph import GraphProjector
from .governance import GovernanceService
from .policy import PolicyEvaluator, Resource
from .proposals import ProposalStore
from .read_support import (
    STAGE_ORDER as _STAGE_ORDER, as_bullets as _as_bullets,
    combine_labels as _combine_labels, embed_body as _embed_body,
    format_money_k as _format_money_k, latest as _latest,
    parse_money_k as _parse_money_k, parse_percent as _parse_percent,
    render_composed_answer as _render_composed_answer,
    strip_first_heading as _strip_first_heading,
)
from .retrieval import Card, Retriever


def _default_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CompanyBriefService:
    def __init__(
        self,
        retriever: Retriever,
        policy: PolicyEvaluator,
        audit: AuditSink,
        proposals: ProposalStore,
        now: Callable[[], str] | None = None,
        field_map: dict | None = None,
        approval_key: bytes | None = None,
    ) -> None:
        self._retriever = retriever
        self._policy = policy
        self._audit = audit
        self._proposals = proposals
        self._now = now or _default_now
        self._fields = (field_map or config.field_extraction()).get("types", {})
        # Write-governance is a separate service; this class is the read facade
        # that delegates proposal/approval/review to it (public API unchanged).
        self._gov = GovernanceService(retriever, policy, audit, proposals, self._now, approval_key)

    @staticmethod
    def _freshness(cards: list[Card]) -> tuple[str, str]:
        """Derive an honest freshness label + as_of date from the emitted cards,
        instead of asserting a constant. 'mixed' when cards disagree."""
        labels = {c.freshness for c in cards if c.freshness}
        updates = sorted(c.updated for c in cards if c.updated)
        if not labels:
            label = "unknown"
        elif len(labels) == 1:
            label = next(iter(labels))
        else:
            label = "mixed"
        return label, (updates[-1] if updates else "")

    def _field(self, card: Card, key: str) -> str:
        """Extract a logical field from a card via the field-extraction profile.
        Returns "" when the type/field is not mapped (callers supply fallbacks)."""
        spec = self._fields.get(card.type, {}).get(key)
        return field_value(card.body, spec) if spec else ""

    # -- reads -------------------------------------------------------------
    def company_search(self, actor, query: str, limit: int = 8) -> dict:
        """Return only company records the actor may discover and open.

        This is intentionally a small deterministic resolver, not semantic
        search.  It never returns a blocked card, a hidden-count hint, or card
        body content.  The browser can safely use the opaque stable id to open
        the existing role-aware GraphView.
        """
        query = query.strip()
        matches: list[dict[str, str]] = []
        for card in self._retriever.candidates(query, "company"):
            decision = self._policy.can_read(actor, self._resource(card))
            self._log(actor, self._resource(card), "company_search", decision)
            if decision.effect != "allow":
                continue
            matches.append({
                "entity_id": card.entity_id,
                "label": card.display,
                "type": "company",
                "freshness": card.freshness,
                "updated": card.updated,
            })
            if len(matches) >= limit:
                break
        return {
            "text": f"Company search: {len(matches)} accessible match(es).",
            "status": "ok",
            "query": query,
            "items": matches,
        }

    def entity_graph(
        self,
        actor,
        entity: str,
        entity_type: str = "company",
        depth: int = 1,
        include: list[str] | None = None,
    ) -> dict:
        """Return an authorized, layout-neutral GraphView for one company.

        The projector performs policy checks before projection.  The callback
        sends those exact decisions through the same audit path as the prose
        read tools, while the rendered summary below uses only the already
        filtered GraphView envelope.
        """
        projector = GraphProjector(
            self._retriever,
            self._policy,
            field_map={"types": self._fields},
            on_decision=lambda card, decision: self._log(
                actor, self._resource(card), "entity_graph", decision
            ),
        )
        graph = projector.entity_graph(
            actor,
            entity=entity,
            entity_type=entity_type,
            depth=depth,
            include=include,
        )
        summary = graph["summary"]
        lines = [
            f"# {summary['title']}",
            "",
            f"**Conclusion:** {summary['conclusion']}",
            f"**Access:** {graph['access']}",
        ]
        if graph["nodes"]:
            lines.append(
                f"**Graph:** {len(graph['nodes'])} nodes, {len(graph['edges'])} relationships, "
                f"{len(graph['evidence'])} evidence records."
            )
        if summary.get("as_of"):
            lines.append(f"**As of:** {summary['as_of']} | **Freshness:** {summary['freshness']}")
        if graph["restricted"]:
            lines.append(f"**Restricted:** {' '.join(graph['restricted'])}")
        if graph["missing"]:
            lines.append(f"**Missing:** {' '.join(graph['missing'])}")
        if summary.get("next_action"):
            lines.append(f"**Next action:** {summary['next_action']}")
        return {**graph, "text": "\n".join(lines).rstrip() + "\n"}

    def dashboard(self, actor) -> dict:
        """Return a role-shaped dashboard read model.

        Policy checks occur before any account, score history or source label is
        projected.  The browser must render this envelope as-is rather than
        derive a wider dashboard from graph/search responses.
        """
        projector = DashboardProjector(
            self._retriever._root, self._retriever, self._policy,
            on_decision=lambda card, decision: self._log(actor, self._resource(card), "dashboard", decision),
        )
        result = projector.project(actor)
        self._log_digest(actor, "dashboard", "(dashboard)")
        return result

    def guided_answer(self, actor, intent: str, company: str) -> dict:
        """Route one allowlisted assistant prompt to an existing guarded read.

        This is deliberately a menu, not a free-form prompt interpreter.  Each
        handler owns its own policy checks and citations; this facade never
        receives a role, tool name, raw context or model-generated query.
        """
        routes = {
            "account_brief": self.company_brief,
            "what_changed": self.company_brief,
            "next_step": self.company_brief,
            "deal_risk": self.deal_risk,
            "call_prep": self.call_prep,
        }
        handler = routes.get(intent)
        if handler is None:
            raise ValueError("unsupported guided intent")
        answer = handler(actor, company)
        return {**answer, "intent": intent}

    def company_brief(self, actor, query: str) -> dict:
        company = self._retriever.find_company(query)
        if company is None:
            options = self._retriever.candidates(query, "company")
            if len(options) > 1:
                names = ", ".join(sorted(c.display for c in options))
                ans = Answer(
                    title=f"Company Brief: {query}", access="ambiguous",
                    conclusion=f"'{query}' matches more than one company; please pick one.",
                    restricted=[], missing=[f"candidates: {names}"],
                    next_action="re-ask with the exact company name.",
                )
                return {**ans.as_dict(), "company": query}
            ans = Answer.not_found(
                f"Company Brief: {query}",
                "no company card matched your request; create or import this company, or check the name.",
            )
            return {**ans.as_dict(), "company": query}

        company_res = self._resource(company)
        decision = self._policy.can_read(actor, company_res)
        self._log(actor, company_res, "company_brief", decision)
        if decision.effect == "block":
            ans = Answer(
                title=f"Company Brief: {company.display}", access="blocked",
                conclusion=f"Blocked: {decision.reason}.",
                restricted=[f"company summary blocked: {decision.reason}"],
                next_action="request access or ask an authorized colleague.",
            )
            return {**ans.as_dict(), "company": company.display}

        citations: list[Citation] = [Citation(company.boundary, company.rel_path)]
        sections: list[Section] = []
        restricted: list[str] = []
        any_restricted = False

        summary = self._field(company, "summary")
        if summary:
            sections.append(Section("Summary", bullets=_as_bullets(summary)))

        for card in self._retriever.related(company.entity_id):
            res = self._resource(card)
            d = self._policy.can_read(actor, res)
            self._log(actor, res, "company_brief", d)
            if d.effect == "allow":
                section = self._field(card, "detail") or extract_section(card.body, "Live Intelligence")
                # Name the card type so e.g. a lead's score is not mistaken for a
                # company score; skip the prefix when the display already carries it.
                type_label = card.type.replace('-', ' ').title()
                disp = card.display if card.display.lower().startswith(type_label.lower()) else f"{type_label} - {card.display}"
                heading = f"{card.boundary.replace('-', ' ').title()} - {disp}"
                sections.append(Section(heading, bullets=_as_bullets(section)))
                citations.append(Citation(card.boundary, card.rel_path))
            elif d.effect == "handle":
                handle = find_handle(card.body)
                restricted.append(f"Personal-data ({card.display}): available as handle {handle} - request access.")
                citations.append(Citation(card.boundary, handle=handle))
                any_restricted = True
            else:
                restricted.append(f"{card.boundary} details for {company.display} restricted for your role.")
                any_restricted = True

        conclusions = self._field(company, "conclusions")
        conclusion = next((line.strip("- ").strip() for line in conclusions.splitlines() if line.strip().startswith("-")), "See details below.")
        fresh, as_of = self._freshness([company])
        ans = Answer(
            title=f"Company Brief: {company.display}",
            access="sanitized" if any_restricted else "allowed",
            conclusion=conclusion, sections=sections, citations=citations, restricted=restricted,
            freshness=fresh, as_of=as_of,
            next_action="confirm the next step with the account owner.",
        )
        return {**ans.as_dict(), "company": company.display}

    def deal_risk(self, actor, company: str | None = None) -> dict:
        """Risk + next action for deals the actor may see.

        With a company: that company's deal(s). Without: every accessible deal.
        Roles that cannot read any deal get an aggregated count only - never
        named deals or sales-confidential detail.
        """
        if company:
            target = self._retriever.find_company(company)
            if target is None:
                return self._not_found("Deal Risk", company)
            deals = self._retriever.related_by_type(target.entity_id, "deal")
            scope = target.display
        else:
            deals = self._retriever.by_type("deal")
            scope = "all accessible deals"

        allowed: list[Card] = []
        blocked = 0
        for deal in deals:
            res = self._resource(deal)
            decision = self._policy.can_read(actor, res)
            self._log(actor, res, "deal_risk", decision)
            if decision.effect == "allow":
                allowed.append(deal)
            else:
                blocked += 1

        if not allowed:
            # Named-company request the actor cannot see -> a clean block.
            # Cross-company request with nothing visible -> aggregated count only.
            access = "blocked" if company else "aggregated"
            conclusion = (
                "Deal risk for this account is restricted to its sales team."
                if company
                else f"{blocked} deal(s) are at risk but restricted to sales roles."
            )
            ans = Answer(
                title=f"Deal Risk: {scope}", access=access, conclusion=conclusion,
                restricted=[f"{blocked} deal(s) restricted for your role."],
                next_action="ask the account owner, Head of Sales or RevOps for the named detail.",
            )
            return {**ans.as_dict(), "scope": scope}

        rows: list[list[str]] = []
        citations: list[Citation] = []
        for deal in allowed:
            risk = self._field(deal, "risk") or "no explicit risk noted"
            action = self._field(deal, "recommended_action") or "confirm the next step with the owner"
            score = self._field(deal, "score") or "—"
            win = self._field(deal, "win_probability") or "—"
            value = self._field(deal, "acv") or "—"
            rows.append([deal.display, score, win, value, risk, action])
            citations.append(Citation(deal.boundary, deal.rel_path))
        restricted = [f"{blocked} additional deal(s) restricted for your role."] if blocked else []
        fresh, as_of = self._freshness(allowed)
        ans = Answer(
            title=f"Deal Risk: {scope}", access="allowed",
            conclusion=f"{len(allowed)} accessible deal(s) at risk.",
            sections=[Section("Deals At Risk", table=Table(["Deal", "Score", "Win %", "Value", "Risk", "Recommended action"], rows))],
            citations=citations, restricted=restricted, freshness=fresh, as_of=as_of,
            next_action="confirm the next step with each deal owner.",
        )
        return {**ans.as_dict(), "scope": scope}

    def call_prep(self, actor, company: str) -> dict:
        """Sanitized pre-call summary for a company's most recent call.

        Authorized sales get the sanitized takeaway plus an opaque handle to the
        raw transcript (never the raw body). Roles without sales-confidential
        access get only a sanitized "sales feedback" note with no deal detail.
        """
        target = self._retriever.find_company(company)
        if target is None:
            return self._not_found("Call Prep", company)

        calls = self._retriever.related_by_type(target.entity_id, "call")
        if not calls:
            ans = Answer.not_found(
                f"Call Prep: {target.display}",
                "no call card is linked to this account yet.",
            )
            return {**ans.as_dict(), "company": target.display}

        call = calls[0]
        res = self._resource(call)
        decision = self._policy.can_read(actor, res)
        self._log(actor, res, "call_prep", decision)

        if decision.effect != "allow":
            # Sanitized note only: name the (broad) account, expose no deal detail.
            ans = Answer(
                title=f"Call Prep: {target.display}", access="sanitized",
                conclusion="Sales feedback only: call notes for this account are sanitized and limited to the sales team.",
                restricted=["named call detail restricted for your role."],
                next_action="ask the account owner for a shareable summary.",
            )
            return {**ans.as_dict(), "company": target.display}

        takeaway = self._field(call, "takeaway") or "see the account owner for context"
        action = self._field(call, "recommended_action") or "confirm the next step with the owner"
        handle = find_handle(call.body)
        fresh, as_of = self._freshness([call])
        ans = Answer(
            title=f"Call Prep: {target.display}", access="allowed", conclusion=takeaway,
            sections=[Section("Sanitized Call Notes", bullets=[f"Sanitized takeaway: {takeaway}", f"Recommended action: {action}"])],
            citations=[Citation(call.boundary, call.rel_path)],
            restricted=[f"Raw transcript: available as handle {handle} - request access."],
            freshness=fresh, as_of=as_of,
            next_action="confirm the next step with the owner.",
        )
        return {**ans.as_dict(), "company": target.display}

    def lead_priority(self, actor, company: str | None = None) -> dict:
        """Ranked MQL leads. The lead list (band, why-now, next action) is broad
        and shared with every role; the contact stays an opaque handle; the
        linked deal's risk is added only for roles that may read that deal.
        """
        if company:
            target = self._retriever.find_company(company)
            if target is None:
                return self._not_found("Lead Priority", company)
            leads = self._retriever.related_by_type(target.entity_id, "lead")
            scope = target.display
        else:
            leads = self._retriever.by_type("lead")
            scope = "all accessible leads"

        band_rank = {"hot": 0, "warm": 1, "cold": 2}

        def band_of(lead: Card) -> str:
            return self._field(lead, "score_band").lower()

        leads = sorted(leads, key=lambda c: band_rank.get(band_of(c), 9))

        citations: list[Citation] = []
        restricted: list[str] = []
        rows: list[list[str]] = []
        for lead in leads:
            if not self._readable(actor, lead, "lead_priority"):
                continue  # fail-safe: never emit a lead the actor may not read
            band = self._field(lead, "score_band") or "unscored"
            score = self._field(lead, "score") or "—"
            stage = self._field(lead, "stage") or "—"
            why = self._field(lead, "why_now") or "no signal recorded"
            action = self._field(lead, "recommended_action") or "confirm the next step"
            citations.append(Citation(lead.boundary, lead.rel_path))
            handle = find_handle(lead.body)
            if handle != "restricted://(unknown)":
                restricted.append(f"Contact for {lead.display}: handle {handle} - request access.")
            risk, deal, allowed = self._linked_deal(actor, lead.company, "lead_priority")
            if allowed and risk:
                # Column is already "Linked deal"; don't prefix the cell (avoids
                # a "Linked deal: Linked deal risk: ..." stutter in the renderer).
                deal_cell = f"at risk — {risk}"
                citations.append(Citation(deal.boundary, deal.rel_path))
            elif deal is not None:
                deal_cell = "restricted for your role"
                restricted.append(f"Linked deal for {lead.display} restricted for your role.")
            else:
                deal_cell = "no linked deal"
            rows.append([lead.display, score, band, stage, why, action, deal_cell])
        fresh, as_of = self._freshness(leads)
        ans = Answer(
            title=f"Lead Priority: {scope}", access="allowed",
            conclusion=f"{len(rows)} lead(s) to act on, highest score first.",
            sections=[Section("Leads", table=Table(["Lead", "Score", "Score band", "Stage", "Why now", "Next action", "Linked deal"], rows))],
            citations=citations, restricted=restricted, freshness=fresh, as_of=as_of,
            next_action="book the highest-band leads this week.",
        )
        return {**ans.as_dict(), "scope": scope}

    def event_brief(self, actor, event: str) -> dict:
        """Event brief: public target accounts for every role, plus private deal
        context per account only for roles that may read that deal.
        """
        return self._target_account_brief(actor, event, "event", "Event Brief", "event_brief")

    def campaign_brief(self, actor, campaign: str) -> dict:
        """Campaign brief: public target accounts and content angle for every
        role, plus private deal context per account only for authorized roles.
        Marketing gets the brief without restricted deal detail.
        """
        return self._target_account_brief(actor, campaign, "campaign", "Campaign Brief", "campaign_brief")

    def content_opportunities(self, actor) -> dict:
        """Broad marketing product: pain points with a content angle and a
        suggested asset. Public-safe, shared with sales and marketing alike.
        """
        pains = self._retriever.by_type("pain-point")
        self._log_digest(actor, "content_opportunities", "(content)")
        citations: list[Citation] = []
        rows: list[list[str]] = []
        for pain in pains:
            if not self._readable(actor, pain, "content_opportunities"):
                continue  # fail-safe: never emit a pain card the actor may not read
            angle = self._field(pain, "content_angle") or "no angle recorded"
            asset = self._field(pain, "suggested_asset") or "blog post"
            rows.append([pain.display, angle, asset])
            citations.append(Citation(pain.boundary, pain.rel_path))
        fresh, as_of = self._freshness(pains)
        ans = Answer(
            title="Content Opportunities", access="allowed",
            conclusion=f"{len(rows)} content opportunity(ies) from known pains.",
            sections=[Section("Opportunities", table=Table(["Pain", "Content angle", "Suggested asset"], rows))],
            citations=citations, freshness=fresh, as_of=as_of,
            next_action="brief the highest-value angle first.",
        )
        return ans.as_dict()

    def _target_account_brief(self, actor, query: str, card_type: str, title: str, tool: str) -> dict:
        """Shared brief for a card that lists Target Accounts (events, campaigns):
        accounts are broad for every role; per-account deal context is added only
        for roles that may read the deal. Marketing gets no restricted detail.
        """
        card = self._retriever.find(query, card_type)
        if card is None:
            return self._not_found(title, query)

        if not self._readable(actor, card, tool):
            # Fail-safe: the brief card itself is in a boundary the actor cannot read.
            ans = Answer(
                title=f"{title}: {card.display}", access="blocked",
                conclusion="This brief is restricted for your role.",
                restricted=[f"{title} restricted for your role."],
            )
            return {**ans.as_dict(), "target": card.display}

        names = wikilink_targets(self._field(card, "target_accounts"), "Company - ")
        angle = self._field(card, "content_angle")

        citations: list[Citation] = [Citation(card.boundary, card.rel_path)]
        restricted: list[str] = []
        rows: list[list[str]] = []
        for name in names:
            company = self._retriever.find_company(name)
            if company is None:
                rows.append([name, "no company card"])
                continue
            risk, deal, allowed = self._linked_deal(actor, company.entity_id, tool)
            if allowed and risk:
                # Header is "Deal context", so don't repeat "deal"; strip the
                # risk's trailing period so it doesn't read as ".;".
                rows.append([name, f"open deal at risk — {risk.rstrip(' .;')}; tie the message to it"])
                citations.append(Citation(deal.boundary, deal.rel_path))
            elif deal is not None:
                # Roles without deal access (e.g. marketing) get the account's
                # broad market signal — a usable per-account angle, not a dead
                # "restricted" line. Deal economics stay sales-confidential.
                signal, src = self._account_signal(actor, company)
                if signal:
                    rows.append([name, f"public angle — {signal.rstrip(' .')}; tie the campaign message to it"])
                    citations.append(Citation(src.boundary, src.rel_path))
                else:
                    rows.append([name, "public angle only — deal economics are sales-confidential"])
            else:
                rows.append([name, "no linked deal"])
        sections = [Section("Target Accounts", table=Table(["Account", "Deal context"], rows))]
        fresh, as_of = self._freshness([card])
        ans = Answer(
            title=f"{title}: {card.display}", access="allowed",
            conclusion=f"{len(names)} target account(s)." + (f" Content angle: {angle}" if angle else ""),
            sections=sections, citations=citations, restricted=restricted, freshness=fresh, as_of=as_of,
            next_action="prep account-specific outreach before the date.",
        )
        return {**ans.as_dict(), "target": card.display}

    def my_day(self, actor) -> dict:
        """Personal "what to do today" digest: the actor's lead priorities and
        their at-risk deals, composed from the access-filtered read products so
        no-leak is inherited (marketing gets leads but no deal detail).
        """
        leads = self.lead_priority(actor, None)
        deals = self.deal_risk(actor, None)
        self._log_digest(actor, "my_day", "(daily-digest)")
        name = actor.name or actor.id
        title = f"My Day: {name}"
        conclusion = "Act on your top leads first, then protect your at-risk deals."
        citations = leads["citations"] + deals["citations"]
        restricted = leads["restricted"] + deals["restricted"]
        freshness = _combine_labels(leads.get("freshness", ""), deals.get("freshness", ""))
        as_of = _latest(leads.get("as_of", ""), deals.get("as_of", ""))
        next_action = (
            "work the highest-priority lead, then confirm the next step on any "
            "visible at-risk deal."
        )
        # Lead the deal section with the conclusion as a plain bullet so it is
        # never blank for roles without deal access (and survives the chat layer
        # stripping the "Restricted For Your Role" section); append the table for
        # roles that do see deals.
        deal_section = f"- {deals['conclusion']}"
        # Drop the embedded sub-answers' own "## Leads" / "## Deals At Risk"
        # headers so they don't double the digest's wrapper headings.
        deal_table = _strip_first_heading(_embed_body(deals["text"]).strip())
        if deal_table:
            deal_section += "\n" + deal_table
        body_lines = [
            "## Leads To Act On", _strip_first_heading(_embed_body(leads["text"]).strip()),
            "## Deal Risk", deal_section,
        ]
        out = Answer(
            title=title,
            access="allowed",
            conclusion=conclusion,
            sections=[
                Section(
                    "Leads To Act On", bullets=[leads["conclusion"]],
                    table=Table(**leads["sections"][0]["table"]) if leads.get("sections") and leads["sections"][0].get("table") else None,
                ),
                Section(
                    "Deal Risk", bullets=[deals["conclusion"]],
                    table=Table(**deals["sections"][0]["table"]) if deals.get("sections") and deals["sections"][0].get("table") else None,
                ),
            ],
            citations=[
                Citation(c.get("boundary", ""), c.get("path", ""), c.get("handle", ""))
                for c in citations
            ],
            restricted=restricted,
            freshness=freshness,
            as_of=as_of,
            next_action=next_action,
        ).as_dict()
        out.update({
            "actor": actor.id,
            "text": _render_composed_answer(
                title, conclusion, body_lines, citations, out["confidence"],
                freshness, as_of, next_action, "allowed",
            ),
        })
        return out

    def _pipeline_metrics(self, actor) -> dict:
        """Quantified rollup over the deals this actor may read. Computed only on
        allowed deals so no value figure leaks to a role without deal access.
        """
        allowed = [
            deal for deal in self._retriever.by_type("deal")
            if self._policy.can_read(actor, self._resource(deal)).effect == "allow"
        ]
        total_k = 0
        weighted_k = 0.0
        by_stage: dict[str, int] = {}
        for deal in allowed:
            value_k = _parse_money_k(self._field(deal, "acv"))
            total_k += value_k
            weighted_k += value_k * _parse_percent(self._field(deal, "win_probability"))
            stage = self._field(deal, "stage") or "Unknown"
            by_stage[stage] = by_stage.get(stage, 0) + 1
        return {"count": len(allowed), "total_k": total_k, "weighted_k": round(weighted_k), "by_stage": by_stage}

    def pipeline_risk_digest(self, actor) -> dict:
        """Aggregate risk view: the deals the actor may read (reused from
        deal_risk), a quantified pipeline rollup over those same deals, plus a
        count of pending proposals awaiting apply.
        """
        deals = self.deal_risk(actor, None)
        pending = [s for s in self._proposals.states().values() if s.get("status") in ("draft", "approved")]
        self._log_digest(actor, "pipeline_risk_digest", "(pipeline)")
        title = "Pipeline Risk Digest"
        # Quantified rollup, only when the actor can read at least one deal so no
        # value figure leaks to a role without deal access.
        metrics = self._pipeline_metrics(actor)
        # A role with no readable deal gets an honest 'restricted' digest, not a
        # generic 'review the deals' conclusion over an empty body (no false empty).
        if metrics["count"]:
            access = "allowed"
            conclusion = "Review the deals at risk and their next steps."
            next_action = "review visible at-risk deals and clear the pending proposal queue."
        else:
            access = deals.get("access", "aggregated") if deals.get("access") != "allowed" else "aggregated"
            conclusion = ("Pipeline value and named deals are restricted for your role "
                          "(no deal access) — aggregated view only.")
            next_action = "request deal access, or use role-appropriate views (e.g. content opportunities)."
        rollup_lines: list[str] = []
        rollup_sections: list[Section] = []
        if metrics["count"]:
            stages = ", ".join(
                f"{stage} {count}" for stage, count in sorted(
                    metrics["by_stage"].items(),
                    key=lambda kv: (_STAGE_ORDER.get(kv[0], 99), kv[0]),
                )
            )
            rollup_bullets = [
                f"Open deals: {metrics['count']}",
                f"Total pipeline: {_format_money_k(metrics['total_k'])}",
                f"Weighted pipeline: {_format_money_k(metrics['weighted_k'])}",
                f"By stage: {stages}",
            ]
            rollup_lines = ["## Pipeline Rollup", *(f"- {b}" for b in rollup_bullets)]
            rollup_sections = [Section("Pipeline Rollup", bullets=rollup_bullets)]
        body_lines = [
            _embed_body(deals["text"]),
            *rollup_lines,
            f"**Pending proposals:** {len(pending)} awaiting approval/apply.",
        ]
        out = Answer(
            title=title,
            access=access,
            conclusion=conclusion,
            sections=[
                Section("Visible Deal Risk", bullets=[deals["conclusion"]]),
                *rollup_sections,
                Section("Governance Queue", bullets=[f"{len(pending)} pending proposal(s) awaiting approval/apply."]),
            ],
            citations=[
                Citation(c.get("boundary", ""), c.get("path", ""), c.get("handle", ""))
                for c in deals["citations"]
            ],
            restricted=deals["restricted"],
            freshness=deals.get("freshness", "unknown"),
            as_of=deals.get("as_of", ""),
            next_action=next_action,
        ).as_dict()
        out["text"] = _render_composed_answer(
            title, conclusion, body_lines, deals["citations"], out["confidence"],
            out["freshness"], out["as_of"], next_action, access,
        )
        return out

    def _log_digest(self, actor, tool: str, resource: str) -> None:
        self._audit.record(
            {
                "timestamp": self._now(),
                "actor": actor.id,
                "role": actor.role,
                "tool": tool,
                "resource": resource,
                "decision": "allow",
            }
        )

    def _linked_deal(self, actor, company_entity_id: str, tool: str):
        """Return (risk, deal_card, allowed) for a company's deal, logging the
        access decision. Used to enrich lead/event answers for authorized roles.
        """
        deals = self._retriever.related_by_type(company_entity_id, "deal")
        if not deals:
            return (None, None, False)
        deal = deals[0]
        decision = self._policy.can_read(actor, self._resource(deal))
        self._log(actor, self._resource(deal), tool, decision)
        if decision.effect == "allow":
            return (self._field(deal, "risk"), deal, True)
        return (None, deal, False)

    @staticmethod
    def _not_found(title: str, query: str) -> dict:
        ans = Answer.not_found(
            f"{title}: {query}",
            "no matching card; create or import it, or check the name.",
        )
        return {**ans.as_dict(), "company": query, "scope": query}

    # -- write-governance (delegated to GovernanceService) -----------------
    def flag_stale_or_wrong(self, actor, target: str, note: str) -> str:
        return self._gov.flag_stale_or_wrong(actor, target, note)

    def request_redaction_review(self, actor, target: str, reason: str) -> str:
        return self._gov.request_redaction_review(actor, target, reason)

    def request_access(self, actor, target: str, reason: str) -> str:
        return self._gov.request_access(actor, target, reason)

    def ingest_resource(self, actor, target: str, note: str) -> str:
        return self._gov.ingest_resource(actor, target, note)

    def approve_proposal(self, actor, proposal_id: str, ttl_days: int | None = None) -> dict:
        return self._gov.approve_proposal(actor, proposal_id, ttl_days)

    def reject_proposal(self, actor, proposal_id: str, reason: str) -> dict:
        return self._gov.reject_proposal(actor, proposal_id, reason)

    def revoke_proposal(self, actor, proposal_id: str, reason: str) -> dict:
        return self._gov.revoke_proposal(actor, proposal_id, reason)

    def proposal_state(self, proposal_id: str) -> dict:
        return self._gov.proposal_state(proposal_id)

    def proposal_states(self) -> dict:
        """All proposal states keyed by id (read-only view over the store)."""
        return self._proposals.states()

    def review_queue(self, actor) -> dict:
        return self._gov.review_queue(actor)

    def get_proposal(self, actor, proposal_id: str) -> dict:
        return self._gov.get_proposal(actor, proposal_id)

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _resource(card: Card) -> Resource:
        return Resource(
            entity_id=card.entity_id,
            boundary=card.boundary,
            owner=card.owner,
            team=card.team,
            company=card.company,
        )

    def _readable(self, actor, card: Card, tool: str) -> bool:
        """Log the access decision for a card and return whether it is readable.
        Fail-safe gate for any tool that emits a card body: only `allow` passes,
        so a card mis-filed into a restricted boundary is never emitted.
        """
        res = self._resource(card)
        decision = self._policy.can_read(actor, res)
        self._log(actor, res, tool, decision)
        return decision.effect == "allow"

    def readable_card_paths(self, actor) -> set[str]:
        """Rel-paths of every card `actor` may read, under the same policy the read
        tools enforce (RBAC boundary + ABAC ownership + live grants). A bulk
        capability query for presenter/teaching surfaces (the chat bridge's
        behind-the-glass reveal) so they gate the per-card reveal on real access,
        not just boundary membership. It emits no card body, so it writes no
        per-card audit decision."""
        return {
            card.rel_path for card in self._retriever.cards()
            if self._policy.can_read(actor, self._resource(card)).effect == "allow"
        }

    def _account_signal(self, actor, company: Card) -> tuple[str, Card | None]:
        """A company's broad market-signal phrase and the source card it came from,
        for non-deal roles (marketing). Broad/public, so it carries no
        sales-confidential detail. The source card is returned so the caller can
        cite it — the phrase is extracted from that card, not the campaign/event."""
        for src in self._retriever.related_by_type(company.entity_id, "source"):
            if self._readable(actor, src, "campaign_brief"):
                signal = self._field(src, "signal")
                if signal:
                    return signal, src
        return "", None

    def _log(self, actor, resource: Resource, tool: str, decision) -> None:
        self._audit.record(
            {
                "timestamp": self._now(),
                "actor": actor.id,
                "role": actor.role,
                "tool": tool,
                "resource": resource.entity_id,
                "boundary": resource.boundary,
                "decision": decision.effect,
                "reason": decision.reason,
            }
        )

def build_default_service(
    vault_root,
    audit_path=None,
    proposal_path=None,
    now: Callable[[], str] | None = None,
) -> CompanyBriefService:
    registry = config.boundary_registry()
    retriever = Retriever(Path(vault_root), registry)
    audit = AuditSink(Path(audit_path) if audit_path else None)
    proposal_file = Path(proposal_path) if proposal_path else Path(vault_root) / ".proposals.jsonl"
    proposals = ProposalStore(proposal_file)
    now_fn = now or _default_now
    # The approval-signing key lives beside the proposal store (or in an injected
    # secret): approvals are signed on issue and verified here, so a forged
    # `approved` line cannot unlock a read. See saleswiki_mcp/signing.py.
    approval_key = signing.resolve_key(proposal_file.parent)
    verify_approval = lambda record: signing.verify(approval_key, record)  # noqa: E731
    # Policy reads active (approved, non-revoked, non-expired, signature-valid)
    # grants from the proposal log so an approval immediately upgrades a matching
    # restricted read to allow for that requester, scoped to company + boundary.
    policy = PolicyEvaluator(
        config.access_policy(),
        grants_provider=lambda: proposals.active_grants(now_fn(), verify=verify_approval),
    )
    return CompanyBriefService(retriever, policy, audit, proposals, now=now_fn, approval_key=approval_key)
