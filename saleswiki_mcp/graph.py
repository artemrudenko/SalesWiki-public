"""Role-aware, layout-neutral GraphView v1 projection.

The projector deliberately accepts the same Retriever and PolicyEvaluator used
by the answer tools.  It never reads Markdown paths directly and never returns a
candidate until policy has allowed that card.  Pixel positions, colors and
other presentation concerns belong to the client adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from . import config
from .formatter import extract_section, field_value
from .policy import Decision, PolicyEvaluator, Resource
from .retrieval import Card, Retriever


MAX_NODES = 40
MAX_EDGES = 80
MAX_EVIDENCE = 12

_CARD_TO_NODE_TYPE = {
    "company": "company",
    "person": "person",
    "lead": "lead",
    "deal": "deal",
    "call": "call",
    "competitor": "competitor",
    "competitor-intel": "competitor",
    "source": "source",
    "event": "event",
    "campaign": "campaign",
    "pain-point": "pain-point",
    "private-case": "case-study",
    "case-study": "case-study",
    "task": "task",
    "claim": "claim",
}
SUPPORTED_INCLUDE = frozenset(set(_CARD_TO_NODE_TYPE.values()) - {"company"})

_EDGE_BY_NODE_TYPE = {
    "person": ("PERSON_WORKS_AT_COMPANY", "works at", "to-root"),
    "lead": ("LEAD_BELONGS_TO_COMPANY", "belongs to", "to-root"),
    "deal": ("DEAL_WITH_COMPANY", "deal with", "to-root"),
    # A ``competitor-intel`` card is evidence about an account and a rival, not
    # itself a company entity.  Keep the relationship honest instead of
    # inventing a company-to-company edge from prose.
    "competitor": ("RELATED_TO", "competitor context", "to-root"),
    "event": ("COMPANY_PARTICIPATES_IN_EVENT", "participates in", "from-root"),
    "campaign": ("CAMPAIGN_TARGETS_COMPANY", "targets", "to-root"),
    "pain-point": ("PAIN_POINT_RELEVANT_TO_COMPANY", "relevant to", "to-root"),
    "task": ("TASK_RELATED_TO_ENTITY", "related to", "to-root"),
}

DecisionCallback = Callable[[Card, Decision], None]


class GraphProjectionError(RuntimeError):
    """Raised when a projected graph would violate its no-dangling contract."""


@dataclass(frozen=True)
class _ProjectedCard:
    card: Card
    node_type: str
    evidence_id: str


class GraphProjector:
    """Project authorized company cards into the GraphView v1 contract."""

    def __init__(
        self,
        retriever: Retriever,
        policy: PolicyEvaluator,
        field_map: dict | None = None,
        on_decision: DecisionCallback | None = None,
    ) -> None:
        self._retriever = retriever
        self._policy = policy
        self._fields = (field_map or config.field_extraction()).get("types", {})
        self._on_decision = on_decision

    def entity_graph(
        self,
        actor,
        entity_type: str = "company",
        entity: str = "",
        depth: int = 1,
        include: Iterable[str] | None = None,
    ) -> dict:
        if entity_type != "company":
            raise ValueError("GraphView v1 supports only company roots")
        if depth != 1:
            raise ValueError("GraphView v1 supports only depth=1")
        requested = self._normalize_include(include)

        candidates = self._retriever.candidates(entity, "company")
        company = self._retriever.find_company(entity)
        if company is None:
            access = "ambiguous" if len(candidates) > 1 else "not-found"
            return self._empty(
                access=access,
                title="Company selection required" if access == "ambiguous" else "Company not found",
                conclusion=(
                    "More than one company matches this request."
                    if access == "ambiguous"
                    else "No company card matched this request."
                ),
                missing=[
                    "use an exact company entity ID"
                    if access == "ambiguous"
                    else "create, import, or check the company name"
                ],
            )

        root_decision = self._decide(actor, company)
        if root_decision.effect != "allow" or not company.entity_id:
            # A blocked response must not echo the card's stable ID, display name,
            # path or policy reason: each can reveal a protected record.
            return self._empty(
                access="blocked",
                title="Restricted company",
                conclusion="This company is not available for your role.",
                restricted=["Root company access is restricted."],
            )

        projected: list[_ProjectedCard] = [
            _ProjectedCard(company, "company", self._evidence_id(0))
        ]
        restricted = []
        projection_gap = False
        authorized_overflow = False
        emitted_ids = {company.entity_id}

        # Sort before policy/projecting so output and response-size decisions are
        # deterministic. Excluded display types are not retrieval candidates for
        # this request and therefore are neither read nor returned.
        related = sorted(
            self._retriever.related(company.entity_id),
            key=lambda card: (card.type, card.entity_id, card.rel_path),
        )
        for card in related:
            node_type = _CARD_TO_NODE_TYPE.get(card.type)
            if node_type is None or node_type not in requested:
                continue
            decision = self._decide(actor, card)
            if decision.effect != "allow":
                if not restricted:
                    restricted.append("Some related records are restricted for your role.")
                continue
            if not card.entity_id or card.entity_id in emitted_ids:
                projection_gap = True
                continue
            # Every emitted node/edge has its own authorized card citation.  The
            # evidence ceiling therefore safely bounds the useful slice before
            # the looser node/edge ceilings are reached.
            if len(projected) >= min(MAX_NODES, MAX_EVIDENCE):
                authorized_overflow = True
                continue
            projected.append(_ProjectedCard(card, node_type, self._evidence_id(len(projected))))
            emitted_ids.add(card.entity_id)

        nodes = [self._node(item) for item in projected]
        temperature, temperature_reason = self._temperature(projected)
        nodes[0]["metadata"].update({
            "temperature": temperature,
            "temperature_reason": temperature_reason,
        })
        evidence = [self._evidence(item) for item in projected]
        edges = [
            self._edge(company.entity_id, item, index)
            for index, item in enumerate(projected[1:], start=1)
        ][:MAX_EDGES]

        cards = [item.card for item in projected]
        freshness, as_of = self._freshness(cards)
        conclusion = self._first_bullet(self._field(company, "conclusions")) or self._detail(company)
        next_action = self._next_action(projected[1:])
        score = self._score(projected[1:])
        missing = []
        if not projected[1:]:
            missing.append("no authorized related records matched the requested types")
        if authorized_overflow:
            missing.append("additional related records were omitted by the GraphView v1 response limit")
        if projection_gap:
            missing.append("some authorized related records could not be projected safely")

        graph = {
            "contract": "saleswiki.graph-view",
            "version": 1,
            "root_id": company.entity_id,
            "access": "sanitized" if restricted else "allowed",
            "summary": {
                "title": company.display,
                "conclusion": conclusion or "Review the linked evidence and account context.",
                "confidence": self._confidence(company),
                "freshness": freshness,
                "as_of": as_of,
                "next_action": next_action or "Confirm the next step with the account owner.",
                "score": score,
            },
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "restricted": restricted,
            "missing": missing,
        }
        self._validate(graph)
        return graph

    def _normalize_include(self, include: Iterable[str] | None) -> frozenset[str]:
        if include is None:
            return SUPPORTED_INCLUDE
        values = frozenset(str(value).strip() for value in include)
        unknown = values - SUPPORTED_INCLUDE
        if unknown:
            raise ValueError(f"unsupported GraphView include type(s): {', '.join(sorted(unknown))}")
        return values

    def _decide(self, actor, card: Card) -> Decision:
        decision = self._policy.can_read(actor, self._resource(card))
        if self._on_decision is not None:
            self._on_decision(card, decision)
        return decision

    @staticmethod
    def _resource(card: Card) -> Resource:
        return Resource(
            entity_id=card.entity_id,
            boundary=card.boundary,
            owner=card.owner,
            team=card.team,
            company=card.company,
        )

    def _node(self, item: _ProjectedCard) -> dict:
        card = item.card
        metadata: dict[str, str | int | bool | None] = {
            "boundary": card.boundary,
            "freshness": card.freshness or "unknown",
            "updated": card.updated or "",
        }
        if card.owner:
            metadata["owner"] = card.owner
        if card.team:
            metadata["team"] = card.team
        for key in ("stage", "score", "score_band", "acv", "win_probability"):
            value = self._field(card, key)
            if value:
                metadata[key] = self._number(value) if key == "score" else value
        return {
            "id": card.entity_id,
            "type": item.node_type,
            "label": self._label(card),
            "subtitle": card.type.replace("-", " ").title(),
            "detail": self._detail(card),
            "metadata": metadata,
            "evidence_ids": [item.evidence_id],
        }

    def _edge(self, root_id: str, item: _ProjectedCard, index: int) -> dict:
        edge_type, label, direction = _EDGE_BY_NODE_TYPE.get(
            item.node_type, ("RELATED_TO", "related to", "to-root")
        )
        if direction == "from-root":
            source, target = root_id, item.card.entity_id
        else:
            source, target = item.card.entity_id, root_id
        return {
            "id": f"edge-{index}",
            "type": edge_type,
            "from": source,
            "to": target,
            "label": label,
            "evidence_ids": [item.evidence_id],
        }

    @staticmethod
    def _evidence(item: _ProjectedCard) -> dict:
        card = item.card
        return {
            "id": item.evidence_id,
            "title": GraphProjector._label(card),
            # Freshness says when a record was reviewed, not whether its claims
            # were independently verified. Card currently exposes no canonical
            # verification field, so the honest default is needs-review.
            "status": "needs-review",
            "as_of": card.updated or "",
            "summary": GraphProjector._clip(GraphProjector._detail_static(card), 240),
            "citation": {"boundary": card.boundary, "path": card.rel_path},
        }

    def _detail(self, card: Card) -> str:
        detail = self._field(card, "detail") or self._detail_static(card)
        return self._clip(" ".join(line.strip().lstrip("- ") for line in detail.splitlines() if line.strip()), 300)

    @staticmethod
    def _detail_static(card: Card) -> str:
        for heading in ("Live Intelligence", "Deal Readout", "Executive Summary", "Source Summary", "Scoring"):
            section = extract_section(card.body, heading)
            if section:
                return section
        return "Authorized SalesWiki record."

    def _field(self, card: Card, key: str) -> str:
        spec = self._fields.get(card.type, {}).get(key)
        return field_value(card.body, spec) if spec else ""

    def _next_action(self, related: list[_ProjectedCard]) -> str:
        for wanted in ("deal", "call", "lead", "task"):
            for item in related:
                if item.node_type == wanted:
                    action = self._field(item.card, "recommended_action")
                    if action:
                        return action
        return ""

    def _score(self, related: list[_ProjectedCard]) -> int | float | None:
        for wanted in ("deal", "lead"):
            for item in related:
                if item.node_type == wanted:
                    value = self._field(item.card, "score")
                    number = self._number(value)
                    if isinstance(number, (int, float)) and 0 <= number <= 100:
                        return number
        return None

    def _confidence(self, company: Card) -> str:
        section = self._field(company, "conclusions")
        for line in section.splitlines():
            if "confidence:" in line.lower():
                value = line.split(":", 1)[1].strip().lower()
                if value in {"low", "medium", "high", "unknown"}:
                    return value
        return "unknown"

    def _temperature(self, projected: list[_ProjectedCard]) -> tuple[str, str]:
        """Return a human-readable, access-filtered account temperature.

        This is presentation metadata, not a new scoring model: it only reflects
        already-projected cards. A role cannot infer a hidden deal risk because
        blocked cards never reach this function.
        """
        related = projected[1:]
        for item in related:
            if item.node_type == "deal":
                risk = self._field(item.card, "risk")
                if risk:
                    return "at-risk", "A visible deal has an unresolved risk."
        leads = [item for item in related if item.node_type == "lead"]
        bands = {self._field(item.card, "score_band").lower() for item in leads}
        if "hot" in bands:
            return "hot", "A visible lead has a hot score band and an active next action."
        if "warm" in bands:
            return "warm", "A visible lead is qualified, but needs the next action to stay active."
        if any(item.card.freshness == "stale" for item in projected):
            return "cold", "The visible account context is stale; refresh it before acting."
        if leads:
            return "cold", "No fresh high-priority signal is visible for this account."
        return "warm", "The account has visible context, but no scored lead yet."

    @staticmethod
    def _freshness(cards: list[Card]) -> tuple[str, str]:
        labels = {card.freshness for card in cards if card.freshness}
        freshness = next(iter(labels)) if len(labels) == 1 else ("mixed" if labels else "unknown")
        dates = sorted(card.updated for card in cards if card.updated)
        return freshness, (dates[-1] if dates else "")

    @staticmethod
    def _first_bullet(text: str) -> str:
        return next((line.strip().lstrip("- ").strip() for line in text.splitlines() if line.strip().startswith("-")), "")

    @staticmethod
    def _number(value: str) -> int | float | str:
        raw = value.strip().rstrip("%")
        try:
            number = float(raw)
            return int(number) if number.is_integer() else number
        except ValueError:
            return value

    @staticmethod
    def _label(card: Card) -> str:
        label = card.display
        for prefix in ("Competitor Intel - ", "Private Case - "):
            if label.startswith(prefix):
                label = label[len(prefix):]
        return label

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        clean = " ".join(text.split())
        return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"

    @staticmethod
    def _evidence_id(index: int) -> str:
        return f"evidence-{index + 1}"

    @staticmethod
    def _empty(
        access: str,
        title: str,
        conclusion: str,
        restricted: list[str] | None = None,
        missing: list[str] | None = None,
    ) -> dict:
        graph = {
            "contract": "saleswiki.graph-view",
            "version": 1,
            "root_id": None,
            "access": access,
            "summary": {
                "title": title,
                "conclusion": conclusion,
                "confidence": "unknown",
                "freshness": "unknown",
                "as_of": "",
                "next_action": "Request access." if access == "blocked" else "Provide an exact company identifier.",
                "score": None,
            },
            "nodes": [],
            "edges": [],
            "evidence": [],
            "restricted": restricted or [],
            "missing": missing or [],
        }
        GraphProjector._validate(graph)
        return graph

    @staticmethod
    def _validate(graph: dict) -> None:
        if graph.get("contract") != "saleswiki.graph-view" or graph.get("version") != 1:
            raise GraphProjectionError("unsupported GraphView contract")
        allowed_access = {"allowed", "sanitized", "aggregated", "blocked", "not-found", "ambiguous"}
        access = graph.get("access")
        if access not in allowed_access:
            raise GraphProjectionError("invalid GraphView access state")
        node_ids = [node["id"] for node in graph["nodes"]]
        edge_ids = [edge["id"] for edge in graph["edges"]]
        evidence_ids = [item["id"] for item in graph["evidence"]]
        if any(not value for value in [*node_ids, *edge_ids, *evidence_ids]):
            raise GraphProjectionError("empty graph identifier")
        if (
            len(node_ids) != len(set(node_ids))
            or len(edge_ids) != len(set(edge_ids))
            or len(evidence_ids) != len(set(evidence_ids))
        ):
            raise GraphProjectionError("duplicate graph identifier")
        node_set = set(node_ids)
        evidence_set = set(evidence_ids)
        root_id = graph.get("root_id")
        if access in {"allowed", "sanitized"}:
            if not isinstance(root_id, str) or not root_id or root_id not in node_set:
                raise GraphProjectionError("root is not an emitted node")
        else:
            if root_id is not None:
                raise GraphProjectionError("empty access state must not expose a root ID")
            if graph["nodes"] or graph["edges"] or graph["evidence"]:
                raise GraphProjectionError("empty access state must not expose graph records")
        for edge in graph["edges"]:
            if edge["from"] not in node_set or edge["to"] not in node_set:
                raise GraphProjectionError("dangling graph edge")
        for record in [*graph["nodes"], *graph["edges"]]:
            if not set(record["evidence_ids"]).issubset(evidence_set):
                raise GraphProjectionError("dangling evidence reference")
        for item in graph["evidence"]:
            citation = item.get("citation", {})
            refs = [key for key in ("path", "handle") if citation.get(key)]
            if len(refs) != 1:
                raise GraphProjectionError("evidence citation must have exactly one reference")
        if len(node_ids) > MAX_NODES or len(graph["edges"]) > MAX_EDGES or len(evidence_ids) > MAX_EVIDENCE:
            raise GraphProjectionError("GraphView response limit exceeded")
