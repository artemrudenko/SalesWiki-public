import assert from "node:assert/strict";
import test from "node:test";
import { createBffSignalReviewClient, createFixtureSignalReviewClient, findReviewSourceNode, validReviewRequest } from "../src/signalReviewClient.js";

const target = "demo-company-atlas-foods";
const request = (changes = {}) => ({ target, action: "start", expected_revision: 0, outcome: "", cause: "unknown", cause_status: "unknown", decision_impact: "not_assessed", next_action: "verify_source", follow_up_on: "2026-10-20", evidence_ids: [], ...changes });
const graphClient = { async getEntityGraph() { return { status: "ready", data: { freshness: "stale", sources: [{ id: "s1", short: "Public audit signal", date: "2026-08-21", boundary: "broad", status: "Verified" }, { id: "s2", short: "Private deal source", date: "2026-08-23", boundary: "sales-confidential", status: "Verified" }] } }; } };

test("source inspection uses IDs even when names collide, and does not invent a missing node", () => {
  const account = { nodes: [{ id: "s1", data: { kind: "source", label: "Duplicate title", evidenceIds: ["e1"] } }, { id: "s2", data: { kind: "source", label: "Duplicate title", evidenceIds: ["e2"] } }] };
  assert.equal(findReviewSourceNode(account, { id: "s2" }).id, "s2");
  assert.equal(findReviewSourceNode(account, { id: "e2" }).id, "s2");
  assert.equal(findReviewSourceNode(account, { id: "missing" }), undefined);
});

test("synthetic review keeps source age and decision separate and resets per person", async () => {
  let person = { id: "p1", role: "sales-owner" };
  const client = createFixtureSignalReviewClient({ graphClient, getPerson: () => person, now: () => "2026-10-12T09:00:00Z" });
  assert.equal((await client.record(request())).status, "ready");
  assert.equal((await client.record(request())).status, "conflict");
  assert.equal((await client.record(request({ action: "complete", expected_revision: 1, outcome: "update_needed", decision_impact: "changed", next_action: "propose_update", evidence_ids: ["s1"] }))).status, "ready");
  const view = (await client.get({ target })).data;
  assert.equal(view.state, "completed");
  assert.equal(view.card_freshness, "stale");
  assert.equal(view.events.length, 2);
  assert.equal(view.events.at(-1).evidence_dates.s1, "2026-08-21");
  person = { id: "p2", role: "marketing" };
  const marketing = (await client.get({ target })).data;
  assert.equal(marketing.events.length, 0);
  assert.deepEqual(marketing.sources.map((source) => source.id), ["s1"]);
  await client.record(request());
  assert.equal((await client.record(request({ action: "complete", expected_revision: 1, outcome: "confirmed_current", decision_impact: "unchanged", next_action: "none", follow_up_on: "", evidence_ids: ["s2"] }))).status, "error");
});

test("completion needs an active check; unknown evidence stays unknown", async () => {
  const client = createFixtureSignalReviewClient({ graphClient, getPerson: () => ({ id: "p1", role: "sales-owner" }), now: () => "2026-10-12T09:00:00Z" });
  const complete = request({ action: "complete", outcome: "unable_to_verify", decision_impact: "cannot_assess", next_action: "request_context" });
  assert.equal((await client.record(complete)).status, "conflict");
  await client.record(request());
  assert.equal((await client.record({ ...complete, expected_revision: 1 })).status, "ready");
  const event = (await client.get({ target })).data.events.at(-1);
  assert.equal(event.cause, "unknown");
  assert.equal(event.outcome, "unable_to_verify");
  assert.equal(event.next_action, "request_context");
});

test("bad inputs, unsupported certainty and impossible dates are rejected", () => {
  for (const change of [{ role: "admin" }, { follow_up_on: "2026-02-30" }, { cause: "sync_failed", cause_status: "confirmed" }, { expected_revision: true }, { next_action: "none" }, { outcome: "private notes" }]) assert.equal(validReviewRequest(request(change)), false);
});

test("BFF writes only operational fields and does not claim an ambiguous save succeeded", async () => {
  const calls = [];
  const client = createBffSignalReviewClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url, options) => { calls.push({ url, options }); return { ok: true, async json() { return { status: "recorded", access: "allowed", revision: 1, state: "in_progress" }; } }; } });
  assert.equal((await client.record(request())).status, "ready");
  assert.equal(calls[0].url, "/api/v1/signal-review");
  const sent = JSON.parse(calls[0].options.body);
  assert.equal(Object.hasOwn(sent, "role"), false);
  assert.equal(Object.hasOwn(sent, "actor_id"), false);
  assert.equal(Object.hasOwn(sent, "note"), false);
  const uncertain = createBffSignalReviewClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async () => ({ ok: true, async json() { return { status: "recorded" }; } }) });
  assert.equal((await uncertain.record(request())).status, "error");
  assert.throws(() => createBffSignalReviewClient({ endpoint: "https://name:secret@example.com/api/v1/entity-graph" }));
});

test("persona switching while recording cannot reassign the event", async () => {
  let person = { id: "p1", role: "sales-owner" };
  let finish;
  const delayed = { getEntityGraph: () => new Promise((resolve) => { finish = () => resolve(graphClient.getEntityGraph()); }) };
  const client = createFixtureSignalReviewClient({ graphClient: delayed, getPerson: () => person });
  const saved = client.record(request());
  person = { id: "p2", role: "marketing" };
  finish();
  assert.equal((await saved).status, "error");
});
