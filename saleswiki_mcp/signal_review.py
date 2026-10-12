"""Personal, permissioned quality-review journal; never writes evidence/cards.

Only enums and authorized source IDs are accepted. The server supplies identity
and time. A compare-and-append revision prevents two tabs overwriting a check.
This operational history is separate from the security/access audit.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .jsonl import append_computed, read_records_checked
from .policy import Resource

OUTCOMES = {"confirmed_current", "update_needed", "no_longer_relevant", "unable_to_verify", "false_alarm"}
CAUSES = {"unknown", "old_source", "source_changed", "sync_failed", "no_owner", "missed_task", "wrong_cadence", "conflicting_sources", "false_alert"}
CAUSE_STATUSES = {"unknown", "suspected", "confirmed"}
IMPACTS = {"not_assessed", "unchanged", "changed", "cannot_assess"}
NEXT_ACTIONS = {"verify_source", "reconcile_summary", "propose_update", "request_context", "revisit_later", "none"}
FIELDS = {"target", "action", "expected_revision", "outcome", "cause", "cause_status", "decision_impact", "next_action", "follow_up_on", "evidence_ids"}


def validate_request(request: dict) -> dict:
    if not isinstance(request, dict) or set(request) != FIELDS:
        raise ValueError("invalid_signal_review")
    value = dict(request)
    if (not isinstance(value["target"], str) or not value["target"] or len(value["target"]) > 160
            or any(ord(c) < 32 for c in value["target"])):
        raise ValueError("invalid_signal_review")
    if type(value["expected_revision"]) is not int or value["expected_revision"] < 0:
        raise ValueError("invalid_signal_review")
    if value["action"] not in ("start", "complete"):
        raise ValueError("invalid_signal_review")
    enums = {"cause": CAUSES, "cause_status": CAUSE_STATUSES, "decision_impact": IMPACTS, "next_action": NEXT_ACTIONS}
    if any(not isinstance(value[key], str) or value[key] not in choices for key, choices in enums.items()):
        raise ValueError("invalid_signal_review")
    if not isinstance(value["outcome"], str) or value["outcome"] not in OUTCOMES | {""}:
        raise ValueError("invalid_signal_review")
    refs = value["evidence_ids"]
    if (not isinstance(refs, list) or len(refs) > 8
            or any(not isinstance(ref, str) or not ref or len(ref) > 160 for ref in refs)
            or len(set(refs)) != len(refs)):
        raise ValueError("invalid_signal_review")
    follow_up = value["follow_up_on"]
    if not isinstance(follow_up, str):
        raise ValueError("invalid_signal_review")
    if follow_up:
        try:
            if date.fromisoformat(follow_up).isoformat() != follow_up:
                raise ValueError
        except ValueError as exc:
            raise ValueError("invalid_signal_review") from exc
    if (value["cause_status"] == "unknown") != (value["cause"] == "unknown"):
        raise ValueError("invalid_signal_review")
    if value["cause_status"] != "unknown" and not refs:
        raise ValueError("invalid_signal_review")
    if value["action"] == "start":
        if value["outcome"] or value["cause"] != "unknown" or value["decision_impact"] != "not_assessed" or refs:
            raise ValueError("invalid_signal_review")
        if value["next_action"] == "none":
            raise ValueError("invalid_signal_review")
    else:
        if not value["outcome"] or value["decision_impact"] == "not_assessed":
            raise ValueError("invalid_signal_review")
        if value["outcome"] in {"confirmed_current", "update_needed", "false_alarm"} and not refs:
            raise ValueError("invalid_signal_review")
        if value["outcome"] in {"unable_to_verify", "update_needed"} and value["next_action"] == "none":
            raise ValueError("invalid_signal_review")
    if value["next_action"] != "none" and not follow_up:
        raise ValueError("invalid_signal_review")
    if value["next_action"] == "none" and follow_up:
        raise ValueError("invalid_signal_review")
    return value


class SignalReviewService:
    def __init__(self, retriever, policy, audit, path: Path, now):
        self.retriever, self.policy, self.audit, self.path, self.now = retriever, policy, audit, path, now

    def _card(self, actor, target, tool="signal_review"):
        # Exact IDs only; missing and denied targets have the same public shape.
        card = next((c for c in self.retriever.cards() if c.entity_id == target and c.type == "company"), None)
        resource = Resource(card.entity_id, card.boundary, card.owner, card.team, card.company) if card else None
        permitted = self.policy.can_record_quality_review(actor).effect == "allow"
        allowed = bool(card and permitted and self.policy.can_read(actor, resource).effect == "allow")
        self.audit.record({"timestamp": self.now(), "actor": actor.id, "role": actor.role,
                           "tool": tool, "resource": target, "decision": "allow" if allowed else "block"})
        return card if allowed else None

    def _sources(self, actor, target):
        return [c for c in self.retriever.related_by_type(target, "source")
                if self.policy.can_read(actor, Resource(c.entity_id, c.boundary, c.owner, c.team, c.company)).effect == "allow"]

    @staticmethod
    def _history(records, actor_id, target):
        return [r for r in records if r.get("actor_id") == actor_id and r.get("target") == target]

    def _records(self):
        records, intact = read_records_checked(self.path)
        if not intact:
            return [], False
        try:
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError
                extras = {"actor_id", "recorded_at", "assigned_at", "state", "revision", "evidence_dates"}
                validate_request({k: v for k, v in record.items() if k not in extras})
                if set(record) != FIELDS | extras or record["state"] not in {"in_progress", "completed"}:
                    raise ValueError
                dates = record["evidence_dates"]
                if not isinstance(dates, dict) or set(dates) != set(record["evidence_ids"]) or not all(isinstance(d, str) for d in dates.values()):
                    raise ValueError
            return records, True
        except (ValueError, TypeError):
            return [], False

    def get(self, actor, target):
        card = self._card(actor, target)
        if card is None:
            return {"status": "unavailable", "access": "blocked"}
        records, intact = self._records()
        if not intact:
            return {"status": "error", "access": "allowed"}
        history = self._history(records, actor.id, target)
        # Do not expose an event that refers to a source no longer accessible.
        sources = self._sources(actor, target)
        source_ids = {c.entity_id for c in sources}
        if any(not set(r["evidence_ids"]).issubset(source_ids) for r in history):
            return {"status": "unavailable", "access": "blocked"}
        events = [{k: v for k, v in r.items() if k != "actor_id"} for r in history]
        latest = events[-1] if events else None
        return {"contract": "saleswiki.signal-review", "version": 1, "status": "ok", "access": "allowed",
                "target": target, "revision": len(history), "state": latest["state"] if latest else "not_started",
                "events": events[-20:], "sources": [{"id": c.entity_id, "label": c.display, "date": c.updated} for c in sources],
                "can_start": not history or history[-1]["state"] == "completed",
                "can_complete": bool(history and history[-1]["state"] == "in_progress"),
                "scope": "own_checks", "card_freshness": card.freshness}

    def record(self, actor, request):
        value = validate_request(request)
        target = value["target"]
        if self._card(actor, target, "record_signal_review") is None:
            return {"status": "unavailable", "access": "blocked"}
        sources = self._sources(actor, target)
        source_ids = {c.entity_id for c in sources}
        if not set(value["evidence_ids"]).issubset(source_ids):
            return {"status": "unavailable", "access": "blocked"}
        records, intact = self._records()
        if not intact:
            return {"status": "error", "access": "allowed"}
        if any(not set(r["evidence_ids"]).issubset(source_ids) for r in self._history(records, actor.id, target)):
            return {"status": "unavailable", "access": "blocked"}
        timestamp = self.now()
        if value["follow_up_on"] and value["follow_up_on"] < timestamp[:10]:
            raise ValueError("invalid_signal_review")
        response = {"status": "conflict", "access": "allowed"}

        def compute(records):
            history = self._history(records, actor.id, target)
            if len(history) != value["expected_revision"]:
                return None
            active = bool(history and history[-1]["state"] == "in_progress")
            if (value["action"] == "start" and active) or (value["action"] == "complete" and not active):
                return None
            event = {**value, "actor_id": actor.id, "recorded_at": timestamp,
                     "evidence_dates": {c.entity_id: c.updated for c in sources if c.entity_id in value["evidence_ids"]},
                     "state": "in_progress" if value["action"] == "start" else "completed",
                     "revision": len(history) + 1, "assigned_at": timestamp if value["action"] == "start" else history[-1]["assigned_at"]}
            response.update(status="recorded", revision=event["revision"], state=event["state"])
            return event

        append_computed(self.path, compute)
        return response
