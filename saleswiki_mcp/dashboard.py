"""Policy-filtered dashboard projection.

The dashboard is a read model, not a client-side aggregation shortcut.  It
reads append-only observations from a vault-local JSONL file, filters every
company and related card through the normal policy evaluator, and returns only
the small decision surface the Workbench needs.
"""

from __future__ import annotations

import json
from pathlib import Path

from .policy import PolicyEvaluator, Resource
from .retrieval import Card, Retriever


OBSERVATIONS_PATH = Path("state/dashboard-observations.jsonl")
COMMERCIAL_ROLES = frozenset({"sales-owner", "sales", "hos", "revops", "curator", "admin"})


def _resource(card: Card) -> Resource:
    return Resource(card.entity_id, card.boundary, card.owner, card.team, card.company)


def _read_observations(root: Path) -> list[dict]:
    """Read only well-formed, deliberately small observation records.

    A malformed line is ignored rather than becoming a false data point.  The
    ingestion path is responsible for recording a review/audit event.
    """
    path = root / OBSERVATIONS_PATH
    if not path.is_file():
        return []
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        company_id, observed_on, score = value.get("company_id"), value.get("observed_on"), value.get("score")
        if (
            isinstance(company_id, str) and isinstance(observed_on, str)
            and isinstance(score, int) and 0 <= score <= 100
            and len(company_id) <= 200 and len(observed_on) == 10
        ):
            rows.append({"company_id": company_id, "observed_on": observed_on, "score": score})
    return rows


class DashboardProjector:
    """Build the narrow ``saleswiki.dashboard-view`` response after policy checks."""

    def __init__(self, root: Path, retriever: Retriever, policy: PolicyEvaluator, on_decision=None) -> None:
        self._root = Path(root)
        self._retriever = retriever
        self._policy = policy
        self._on_decision = on_decision or (lambda _card, _decision: None)

    def _allowed(self, actor, card: Card) -> bool:
        decision = self._policy.can_read(actor, _resource(card))
        self._on_decision(card, decision)
        return decision.effect == "allow"

    def project(self, actor) -> dict:
        companies = [card for card in self._retriever.by_type("company") if self._allowed(actor, card)]
        allowed_ids = {card.entity_id for card in companies}
        observations = [row for row in _read_observations(self._root) if row["company_id"] in allowed_ids]
        history: dict[str, list[dict]] = {}
        for row in observations:
            history.setdefault(row["company_id"], []).append(row)
        for rows in history.values():
            rows.sort(key=lambda row: row["observed_on"])

        risk: list[dict] = []
        coverage: list[dict] = []
        signals: list[dict] = []
        as_of = ""
        for company in companies:
            related = self._retriever.related(company.entity_id)
            allowed_related = [card for card in related if self._allowed(actor, card)]
            deals = [card for card in allowed_related if card.type == "deal"]
            sources = [card for card in allowed_related if card.type == "source"]
            tasks = [card for card in allowed_related if card.type == "task"]
            company_history = history.get(company.entity_id, [])
            if actor.role in COMMERCIAL_ROLES and deals and len(company_history) >= 2:
                scores = [row["score"] for row in company_history[-7:]]
                risk.append({
                    "entity_id": company.entity_id,
                    "label": company.display,
                    "history": scores,
                    "delta": scores[-1] - scores[0],
                    "score": scores[-1],
                    "as_of": company_history[-1]["observed_on"],
                })
            coverage.append({
                "entity_id": company.entity_id,
                "label": company.display,
                "economic_buyer": bool(deals and "engaged" in " ".join(card.body.lower() for card in deals)),
                "next_step": bool(tasks or deals),
                "verified_evidence": len(sources) >= 1,
                "monitoring": bool(sources),
            })
            for source in sources:
                date = source.updated or company.updated
                if date:
                    as_of = max(as_of, date)
                signals.append({
                    "id": source.entity_id,
                    "entity_id": company.entity_id,
                    "account": company.display,
                    "title": source.display,
                    "as_of": date,
                    "freshness": source.freshness or "unknown",
                })

        risk.sort(key=lambda row: (row["delta"], -row["score"], row["label"]))
        signals.sort(key=lambda row: (row["as_of"], row["title"]), reverse=True)
        latest_observation = max((row["observed_on"] for row in observations), default="")
        return {
            "contract": "saleswiki.dashboard-view",
            "version": 1,
            "access": "allowed",
            "synthetic": (self._root / "README.txt").is_file(),
            "as_of": max(as_of, latest_observation),
            "risk": risk[:6],
            "coverage": coverage[:12],
            "signals": signals[:8],
            "history_status": "available" if risk else "insufficient-history",
            "text": "Dashboard view contains only policy-filtered, cited decision signals.",
        }
