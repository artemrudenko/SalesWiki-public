import assert from "node:assert/strict";
import test from "node:test";

import { createBffAccountBriefClient, createBffCompanySearchClient, createBffDashboardClient, createBffGuidedAnswerClient, createBffImportClient, createBffReviewClient, createBffSessionClient, createBffUpdateClient, createFixtureCompanySearchClient, createFixtureDailyClient, createFixtureGraphClient, createFixtureImportClient, createFixtureReviewClient, createFixtureSessionClient, createMcpGraphClient, graphDemoScenarios } from "../src/graphClient.js";

const fixtures = [
  { id: "one", name: "One", code: "COMP-1", nodes: [], edges: [], sources: [] },
  { id: "two", name: "Two", code: "COMP-2", nodes: [], edges: [], sources: [] },
];

test("dashboard client uses a dedicated policy-filtered endpoint", async () => {
  let requestedUrl = "";
  const client = createBffDashboardClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url) => {
    requestedUrl = url;
    return { ok: true, json: async () => ({
      contract: "saleswiki.dashboard-view", version: 1, access: "allowed", synthetic: true,
      history_status: "available", risk: [{ entity_id: "one", label: "One", history: [60, 67], delta: 7, score: 67 }],
      coverage: [{ entity_id: "one", label: "One", economic_buyer: true, next_step: true, verified_evidence: true, monitoring: false }],
      signals: [{ id: "source-1", entity_id: "one", account: "One", title: "Signal", as_of: "2026-08-30", freshness: "fresh" }],
    }) };
  } });
  const result = await client.getDashboard();
  assert.equal(requestedUrl, "/api/v1/dashboard");
  assert.deepEqual(result.data.risk[0], { id: "one", name: "One", history: [60, 67], delta: 7, score: 67 });
});

test("guided assistant sends only an allowlisted intent and current entity", async () => {
  let requestedUrl = "";
  const client = createBffGuidedAnswerClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url) => {
    requestedUrl = url;
    return { ok: true, json: async () => ({ intent: "next_step", access: "allowed", conclusion: "Confirm the next workshop.", citations: [] }) };
  } });
  const result = await client.ask({ intent: "next_step", accountId: "company bluepeak" });
  assert.equal(requestedUrl, "/api/v1/guided-answer?intent=next_step&entity=company%20bluepeak");
  assert.equal(result.data.conclusion, "Confirm the next workshop.");
});

test("fixture client exposes every deterministic UI state", async () => {
  const client = createFixtureGraphClient({ accounts: fixtures, latencyMs: 0 });
  for (const scenario of graphDemoScenarios) {
    const response = await client.getEntityGraph({ accountId: "one", scenario: scenario.value });
    assert.equal(response.status, scenario.value === "stale" || scenario.value === "truncated" ? "ready" : scenario.value);
  }
});

test("fixture client returns explicit not-found instead of falling back", async () => {
  const client = createFixtureGraphClient({ accounts: fixtures, latencyMs: 0 });
  const response = await client.getEntityGraph({ accountId: "missing" });
  assert.equal(response.status, "not-found");
});

test("MCP client keeps transport and presentation adaptation behind one seam", async () => {
  const calls = [];
  const client = createMcpGraphClient({
    invoke: async (name, args) => { calls.push({ name, args }); return { contract: "saleswiki.graph-view", version: 1, source: "raw", access: "allowed" }; },
    adaptGraphView: (value) => ({ id: "adapted", source: value.contract }),
  });
  const response = await client.getEntityGraph({ accountId: "company:one" });
  assert.deepEqual(calls, [{ name: "saleswiki.entity_graph", args: { entity: "company:one", entity_type: "company", depth: 1 } }]);
  assert.deepEqual(response, { status: "ready", data: { id: "adapted", source: "saleswiki.graph-view" }, notices: [] });
});

test("MCP client fails closed when adaptation rejects the contract", async () => {
  const client = createMcpGraphClient({
    invoke: async () => ({ contract: "saleswiki.graph-view", version: 1, access: "allowed" }),
    adaptGraphView: () => { throw Object.assign(new Error("bad contract"), { code: "BAD-VERSION" }); },
  });
  const response = await client.getEntityGraph({ accountId: "company:one" });
  assert.equal(response.status, "contract-error");
  assert.equal(response.reference, "BAD-VERSION");
});

test("MCP client maps empty access states without adapting them", async () => {
  let adapted = 0;
  let graphView = {};
  const client = createMcpGraphClient({
    invoke: async () => graphView,
    adaptGraphView: () => { adapted += 1; return {}; },
  });
  for (const [access, expected] of [["blocked", "blocked"], ["not-found", "not-found"], ["ambiguous", "ambiguous"], ["aggregated", "aggregated"]]) {
    graphView = { contract: "saleswiki.graph-view", version: 1, access, root_id: null, nodes: [], edges: [], evidence: [], summary: { conclusion: `${access} result` } };
    const response = await client.getEntityGraph({ accountId: "company:one" });
    assert.equal(response.status, expected);
  }
  assert.equal(adapted, 0, "empty GraphView states must never reach the layout adapter");
});

test("import client sends only a selected target and reviewed summary", async () => {
  let request;
  const client = createBffImportClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url, options) => {
    request = { url, options };
    return { ok: true, json: async () => ({ status: "draft", proposal_id: "proposal-0009" }) };
  } });
  const result = await client.submit({ target: "company_acme", summary: "company: Acme" });
  assert.deepEqual(result, { status: "ready", proposalId: "proposal-0009" });
  assert.equal(request.url, "/api/v1/import-proposal");
  assert.deepEqual(JSON.parse(request.options.body), { target: "company_acme", summary: "company: Acme" });
});

test("review client keeps queue and decision endpoints separate", async () => {
  const calls = [];
  const client = createBffReviewClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => url.endsWith("review-queue") ? { access: "allowed", can_decide: true, items: [] } : { proposal_id: "proposal-1", status: "approved" } };
  } });
  assert.equal((await client.getQueue()).status, "ready");
  assert.equal((await client.decide({ proposalId: "proposal-1", action: "approve" })).data.status, "approved");
  assert.equal(calls[0].url, "/api/v1/review-queue");
  assert.deepEqual(JSON.parse(calls[1].options.body), { proposal_id: "proposal-1", action: "approve", reason: "" });
});

test("brief and update clients use bounded dedicated endpoints", async () => {
  const calls = [];
  const response = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => url.includes("account-brief") ? { access: "allowed", conclusion: "Brief", citations: [] } : { status: "draft", proposal_id: "proposal-0044" } };
  };
  const brief = createBffAccountBriefClient({ endpoint: "/api/v1/entity-graph", fetchImpl: response });
  const update = createBffUpdateClient({ endpoint: "/api/v1/entity-graph", fetchImpl: response });
  assert.equal((await brief.getBrief({ accountId: "company_acme" })).data.conclusion, "Brief");
  assert.equal((await update.submit({ target: "company_acme", note: "Confirm next step" })).proposalId, "proposal-0044");
  assert.equal(calls[0].url, "/api/v1/account-brief?entity=company_acme");
  assert.deepEqual(JSON.parse(calls[1].options.body), { target: "company_acme", note: "Confirm next step" });
});

test("company search uses a dedicated bounded endpoint and fixture search hides blocked accounts", async () => {
  let requestedUrl = "";
  const bff = createBffCompanySearchClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url) => {
    requestedUrl = url;
    return { ok: true, json: async () => ({ status: "ok", query: "Blue", items: [{ entity_id: "bluepeak", label: "BluePeak", type: "company", freshness: "fresh" }] }) };
  } });
  assert.deepEqual(await bff.search({ query: "Blue" }), { status: "ready", items: [{ id: "bluepeak", label: "BluePeak", freshness: "fresh" }] });
  assert.equal(requestedUrl, "/api/v1/company-search?q=Blue");
  const fixture = createFixtureCompanySearchClient({ accounts: [...fixtures, { id: "bluepeak", name: "BluePeak", code: "COMP-3", nodes: [], edges: [], sources: [] }] });
  await createFixtureSessionClient().switchPersona("demo-olivia-marketing");
  assert.deepEqual((await fixture.search({ query: "Blue" })).items, []);
  await createFixtureSessionClient().switchPersona("demo-ethan-ae");
});

test("demo persona transport sends only an allowlisted actor id, never a role", async () => {
  const calls = [];
  const client = createBffSessionClient({ endpoint: "/api/v1/entity-graph", fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ mode: "demo-fixture", person: { id: "demo-curator", name: "Curator", role: "curator", team: "knowledge" }, can_switch_persona: true, can_review: true, personas: [] }) };
  } });
  assert.equal((await client.getSession()).status, "ready");
  assert.equal((await client.switchPersona("demo-curator")).data.person.role, "curator");
  assert.equal(calls[0].url, "/api/v1/session");
  assert.equal(calls[1].url, "/api/v1/demo-persona");
  assert.deepEqual(JSON.parse(calls[1].options.body), { actor_id: "demo-curator" });
  assert.equal(calls[1].options.credentials, "same-origin");
});

test("fixture persona switch changes access, daily context, review permission, and the shared proposal queue", async () => {
  const session = createFixtureSessionClient();
  const graph = createFixtureGraphClient({ accounts: [...fixtures, { id: "bluepeak", name: "BluePeak", code: "COMP-3", nodes: [], edges: [], sources: [] }], latencyMs: 0 });
  const daily = createFixtureDailyClient({ accounts: fixtures });
  const review = createFixtureReviewClient();
  const intake = createFixtureImportClient();
  await session.switchPersona("demo-olivia-marketing");
  assert.equal((await graph.getEntityGraph({ accountId: "bluepeak" })).status, "blocked");
  const blockedQueue = await review.getQueue();
  assert.equal(blockedQueue.data.access, "blocked");
  assert.equal(blockedQueue.data.can_decide, false);
  assert.deepEqual(blockedQueue.data.items, []);
  assert.match((await daily.getMyDay()).data.title, /Olivia Marketing/);
  const proposal = await intake.submit({ target: "one", summary: "company: One" });
  assert.equal((await review.getQueue()).data.access, "blocked", "a contributor cannot use the reviewer queue to discover proposals");
  await session.switchPersona("demo-sophie-curator");
  assert.equal((await review.getQueue()).data.can_decide, true);
  assert.ok((await review.getQueue()).data.items.some((item) => item.proposal_id === proposal.proposalId));
  assert.equal((await review.decide({ proposalId: proposal.proposalId, action: "approve" })).status, "ready");
  await session.switchPersona("demo-ethan-ae");
});

test("fixture Today dashboard changes its queue, decision lens, and account boundary for each role", async () => {
  const accounts = [
    { id: "bluepeak", name: "BluePeak", score: 74, nodes: [], edges: [], sources: [] },
    { id: "atlas", name: "Atlas", score: 79, nodes: [], edges: [], sources: [] },
    { id: "northstar", name: "Northstar", score: 84, nodes: [], edges: [], sources: [] },
    { id: "summit-grid", name: "Summit", score: 82, nodes: [], edges: [], sources: [] },
  ];
  const session = createFixtureSessionClient();
  const daily = createFixtureDailyClient({ accounts });

  await session.switchPersona("demo-ethan-ae");
  const ae = (await daily.getMyDay()).data;
  assert.equal(ae.workbench.profile.label, "Account executive");
  assert.match(ae.workbench.profile.focus, /active opportunities/i);
  assert.deepEqual(ae.workbench.actions.map((item) => item.name), ["BluePeak", "Summit", "Atlas"]);

  await session.switchPersona("demo-olivia-marketing");
  const marketing = (await daily.getMyDay()).data;
  assert.equal(marketing.workbench.profile.label, "Marketing");
  assert.match(marketing.workbench.profile.focus, /permitted signals/i);
  assert.equal(marketing.workbench.profile.showRisk, false);
  assert.ok(marketing.workbench.actions.every((item) => item.name !== "BluePeak"));
  assert.match(marketing.workbench.actions[0].title, /automation proof angle/i);

  await session.switchPersona("demo-sophie-curator");
  const curator = (await daily.getMyDay()).data;
  assert.equal(curator.workbench.profile.label, "Knowledge curator");
  assert.match(curator.workbench.profile.focus, /traceable/i);
  assert.match(curator.workbench.actions[0].title, /Review competitor evidence/i);
  await session.switchPersona("demo-ethan-ae");
});
