import assert from "node:assert/strict";
import test from "node:test";

import { createBffGraphClient } from "../src/graphClient.js";
import { workbenchProxyTarget } from "../vite.config.mjs";

function jsonResponse(body, { ok = true, status = 200, contentType = "application/json; charset=utf-8" } = {}) {
  return {
    ok,
    status,
    headers: { get: (name) => name.toLowerCase() === "content-type" ? contentType : null },
    json: async () => body,
  };
}

const allowedView = { access: "allowed", contract: "saleswiki.graph-view", version: 1 };

test("BFF transport encodes the stable entity ID and sends no identity or secret fields", async () => {
  const calls = [];
  const client = createBffGraphClient({
    endpoint: "/api/v1/entity-graph",
    adaptGraphView: (view) => ({ id: view.contract }),
    fetchImpl: async (...args) => { calls.push(args); return jsonResponse(allowedView); },
  });

  const response = await client.getEntityGraph({ accountId: "company/BluePeak Energy?#1" });

  assert.equal(response.status, "ready");
  assert.equal(calls[0][0], "/api/v1/entity-graph?entity=company%2FBluePeak%20Energy%3F%231");
  const options = calls[0][1];
  assert.equal(options.method, "GET");
  assert.deepEqual(options.headers, { Accept: "application/json" });
  assert.equal(options.credentials, "same-origin");
  assert.equal("body" in options, false);
  assert.doesNotMatch(JSON.stringify(calls), /actor|role|token|authorization/i);
});

test("BFF transport handles safe access states before graph adaptation", async () => {
  let adapted = 0;
  let access = "blocked";
  const client = createBffGraphClient({
    endpoint: "/api/v1/entity-graph",
    adaptGraphView: () => { adapted += 1; return {}; },
    fetchImpl: async () => jsonResponse({ contract: "saleswiki.graph-view", version: 1, access, root_id: null, nodes: [], edges: [], evidence: [], summary: {} }),
  });

  for (const expected of ["blocked", "not-found", "ambiguous", "aggregated"]) {
    access = expected;
    const response = await client.getEntityGraph({ accountId: "demo-company-bluepeak-energy" });
    assert.equal(response.status, expected);
  }
  assert.equal(adapted, 0);
});

test("BFF transport rejects an empty access state that carries hidden records", async () => {
  const client = createBffGraphClient({
    endpoint: "/api/v1/entity-graph",
    adaptGraphView: () => { throw new Error("must not adapt"); },
    fetchImpl: async () => jsonResponse({
      contract: "saleswiki.graph-view",
      version: 1,
      access: "blocked",
      root_id: null,
      nodes: [{ id: "restricted" }],
      edges: [],
      evidence: [],
      summary: {},
    }),
  });
  const response = await client.getEntityGraph({ accountId: "demo-company-bluepeak-energy" });
  assert.equal(response.status, "contract-error");
  assert.equal(response.reference, "GRAPH-EMPTY-001");
});

test("BFF transport fails closed on HTTP, content-type, and JSON-shape errors", async (t) => {
  const cases = [
    ["HTTP", async () => jsonResponse({}, { ok: false, status: 403 }), "GRAPH-HTTP-001"],
    ["content type", async () => jsonResponse({}, { contentType: "text/html" }), "GRAPH-JSON-001"],
    ["JSON shape", async () => jsonResponse([]), "GRAPH-JSON-002"],
  ];
  for (const [name, fetchImpl, reference] of cases) {
    await t.test(name, async () => {
      const client = createBffGraphClient({ endpoint: "/api/v1/entity-graph", adaptGraphView: (value) => value, fetchImpl });
      const response = await client.getEntityGraph({ accountId: "demo-company-bluepeak-energy" });
      assert.equal(response.status, "contract-error");
      assert.equal(response.reference, reference);
    });
  }
});

test("BFF transport rejects endpoints that embed credentials or query parameters", () => {
  for (const endpoint of [
    "https://user:secret@example.com/api/v1/entity-graph",
    "/api/v1/entity-graph?token=secret",
    "javascript:alert(1)",
  ]) {
    assert.throws(() => createBffGraphClient({ endpoint, adaptGraphView: (value) => value, fetchImpl: async () => {} }));
  }
});

test("BFF transport forwards AbortSignal and lets cancellation escape", async () => {
  const controller = new AbortController();
  const client = createBffGraphClient({
    endpoint: "/api/v1/entity-graph",
    adaptGraphView: (value) => value,
    fetchImpl: async (_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    }),
  });
  const pending = client.getEntityGraph({ accountId: "demo-company-bluepeak-energy", signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { name: "AbortError" });
});

test("Vite development proxy uses a safe local default and accepts an explicit origin", () => {
  assert.equal(workbenchProxyTarget(), "http://127.0.0.1:8787");
  assert.equal(workbenchProxyTarget("https://workbench.internal:9443"), "https://workbench.internal:9443");
  for (const target of [
    "https://user:secret@workbench.internal",
    "https://workbench.internal/api",
    "file:///tmp/workbench.sock",
  ]) {
    assert.throws(() => workbenchProxyTarget(target));
  }
});
