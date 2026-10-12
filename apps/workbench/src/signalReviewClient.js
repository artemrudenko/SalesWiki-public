import { getFixturePerson, safeEndpoint } from "./graphClient.js";
import { fixtureCanSeeCommercial } from "./fixtureView.js";

export const reviewOptions = {
  outcome: { confirmed_current: "Confirmed current", update_needed: "Update needed", no_longer_relevant: "No longer relevant", unable_to_verify: "Could not verify", false_alarm: "False alarm" },
  cause: { unknown: "Unknown", old_source: "Source was already old", source_changed: "Source changed", sync_failed: "Sync failed", no_owner: "No owner recorded", missed_task: "Review task missed", wrong_cadence: "Review window did not fit", conflicting_sources: "Sources disagree", false_alert: "Alert was incorrect" },
  cause_status: { unknown: "Unknown", suspected: "Possible cause", confirmed: "Confirmed cause" },
  decision_impact: { not_assessed: "Not assessed", unchanged: "Next decision stays the same", changed: "Next decision changes", cannot_assess: "Cannot assess yet" },
  next_action: { verify_source: "Check the source", reconcile_summary: "Compare sources with the summary", propose_update: "Propose a card update", request_context: "Ask for missing context", revisit_later: "Check again later", none: "No further check needed" },
};

export function findReviewSourceNode(account, source) {
  return account.nodes.find((node) => node.data.kind === "source" && (node.id === source.id || node.data.evidenceIds?.includes(source.id)));
}

export function validReviewRequest(value) {
  const keys = ["target", "action", "expected_revision", "outcome", "cause", "cause_status", "decision_impact", "next_action", "follow_up_on", "evidence_ids"];
  if (!value || typeof value !== "object" || Object.keys(value).length !== keys.length || !keys.every((key) => Object.hasOwn(value, key))) return false;
  if (typeof value.target !== "string" || !value.target || value.target.length > 160 || !["start", "complete"].includes(value.action) || !Number.isInteger(value.expected_revision) || value.expected_revision < 0) return false;
  if (!["cause", "cause_status", "decision_impact", "next_action"].every((key) => Object.hasOwn(reviewOptions[key], value[key]))) return false;
  if (typeof value.outcome !== "string" || (value.outcome && !Object.hasOwn(reviewOptions.outcome, value.outcome))) return false;
  if (!Array.isArray(value.evidence_ids) || value.evidence_ids.length > 8 || value.evidence_ids.some((id) => typeof id !== "string" || !id || id.length > 160) || new Set(value.evidence_ids).size !== value.evidence_ids.length) return false;
  if ((value.cause === "unknown") !== (value.cause_status === "unknown") || (value.cause_status !== "unknown" && !value.evidence_ids.length)) return false;
  if (typeof value.follow_up_on !== "string" || (value.follow_up_on && (!/^\d{4}-\d{2}-\d{2}$/.test(value.follow_up_on) || !Number.isFinite(Date.parse(value.follow_up_on)) || new Date(value.follow_up_on).toISOString().slice(0, 10) !== value.follow_up_on))) return false;
  if ((value.next_action === "none") !== (value.follow_up_on === "")) return false;
  if (value.action === "start") return !value.outcome && value.cause === "unknown" && value.decision_impact === "not_assessed" && !value.evidence_ids.length && value.next_action !== "none";
  return !!value.outcome && value.decision_impact !== "not_assessed" && (!["confirmed_current", "update_needed", "false_alarm"].includes(value.outcome) || value.evidence_ids.length > 0) && (!["unable_to_verify", "update_needed"].includes(value.outcome) || value.next_action !== "none");
}

export function validateReviewView(value, target) {
  if (!value || value.contract !== "saleswiki.signal-review" || value.version !== 1 || value.status !== "ok" || value.access !== "allowed" || value.target !== target || value.scope !== "own_checks" || !Number.isInteger(value.revision) || value.revision < 0 || !["not_started", "in_progress", "completed"].includes(value.state) || typeof value.can_start !== "boolean" || typeof value.can_complete !== "boolean" || !Array.isArray(value.sources) || !Array.isArray(value.events) || value.events.length > 20) throw new Error("Invalid check response");
  if (value.sources.some((source) => !source || !["id", "label", "date"].every((key) => typeof source[key] === "string"))) throw new Error("Invalid check sources");
  const refs = new Set(value.sources.map((source) => source.id));
  for (const event of value.events) {
    const { recorded_at, assigned_at, revision, state, evidence_dates, ...request } = event;
    if (!validReviewRequest(request) || request.target !== target || typeof recorded_at !== "string" || typeof assigned_at !== "string" || !Number.isInteger(revision) || !["in_progress", "completed"].includes(state) || request.evidence_ids.some((id) => !refs.has(id))) throw new Error("Invalid check history");
    if (!evidence_dates || typeof evidence_dates !== "object" || Object.keys(evidence_dates).length !== request.evidence_ids.length || request.evidence_ids.some((id) => typeof evidence_dates[id] !== "string")) throw new Error("Invalid recorded source dates");
  }
  return value;
}

export function createBffSignalReviewClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const url = safeEndpoint(endpoint).replace(/\/entity-graph$/, "/signal-review");
  return {
    mode: "server",
    async get({ target, signal }) {
      try {
        const response = await fetchImpl(`${url}?target=${encodeURIComponent(target)}`, { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
        const value = await response.json();
        if (!response.ok || value.status !== "ok") return { status: "error" };
        return { status: "ready", data: validateReviewView(value, target) };
      } catch (error) { if (error?.name === "AbortError") throw error; return { status: "error" }; }
    },
    async record(request) {
      if (!validReviewRequest(request)) return { status: "invalid" };
      try {
        const response = await fetchImpl(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(request) });
        const value = await response.json();
        if (response.ok && value.status === "conflict") return { status: "conflict" };
        if (!response.ok || value.status !== "recorded" || value.access !== "allowed" || value.revision !== request.expected_revision + 1 || value.state !== (request.action === "start" ? "in_progress" : "completed")) return { status: "error" };
        return { status: "ready" };
      } catch { return { status: "error" }; }
    },
  };
}

export function createFixtureSignalReviewClient({ graphClient, getPerson = getFixturePerson, now = () => new Date().toISOString() }) {
  const journal = new Map();
  const key = (target) => `${getPerson().id}:${target}`;
  async function context(target) {
    const result = await graphClient.getEntityGraph({ accountId: target });
    if (result.status !== "ready") return null;
    const role = getPerson().role;
    const canSeeCommercial = fixtureCanSeeCommercial(target, role);
    return { target, sources: result.data.sources.filter((source) => source.status !== "Restricted" && (["broad", "internal"].includes(source.boundary) || (source.boundary === "sales-confidential" && canSeeCommercial))).map((source) => ({ id: source.id, label: source.short, date: source.date })), card_freshness: result.data.freshness };
  }
  return {
    mode: "fixture",
    async get({ target }) {
      const ctx = await context(target);
      if (!ctx) return { status: "error" };
      const events = journal.get(key(target)) ?? [];
      const state = events.at(-1)?.state ?? "not_started";
      return { status: "ready", data: validateReviewView({ ...ctx, contract: "saleswiki.signal-review", version: 1, status: "ok", access: "allowed", revision: events.length, state, events: events.slice(-20), scope: "own_checks", can_start: state !== "in_progress", can_complete: state === "in_progress" }, target) };
    },
    async record(request) {
      if (!validReviewRequest(request)) return { status: "invalid" };
      // Snapshot identity before awaiting so a persona switch cannot reassign a request.
      const actorKey = key(request.target);
      const ctx = await context(request.target);
      if (!ctx || actorKey !== key(request.target) || request.evidence_ids.some((id) => !ctx.sources.some((source) => source.id === id))) return { status: "error" };
      const events = journal.get(actorKey) ?? [];
      const active = events.at(-1)?.state === "in_progress";
      if (request.expected_revision !== events.length || (request.action === "start" ? active : !active)) return { status: "conflict" };
      const timestamp = now();
      if (request.follow_up_on && request.follow_up_on < timestamp.slice(0, 10)) return { status: "invalid" };
      const evidence_dates = Object.fromEntries(ctx.sources.filter((source) => request.evidence_ids.includes(source.id)).map((source) => [source.id, source.date]));
      journal.set(actorKey, [...events, { ...request, evidence_dates, recorded_at: timestamp, assigned_at: request.action === "start" ? timestamp : events.at(-1).assigned_at, revision: events.length + 1, state: request.action === "start" ? "in_progress" : "completed" }]);
      return { status: "ready" };
    },
  };
}
