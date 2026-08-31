import assert from "node:assert/strict";
import test from "node:test";

import { accounts } from "../src/data.js";
import { buildFixtureDashboard } from "../src/dashboardInsights.js";

test("fixture dashboard derives coverage, risk movement and dated signals from visible graph records", () => {
  const dashboard = buildFixtureDashboard(accounts.slice(0, 3), { "demo-company-bluepeak-energy": { topics: ["News"] } });
  assert.equal(dashboard.risk.length, 3);
  assert.ok(dashboard.risk.some((item) => item.name === "Atlas Foods" && item.delta < 0));
  const bluepeak = dashboard.coverage.find((item) => item.id === "demo-company-bluepeak-energy");
  assert.deepEqual({ buyer: bluepeak.buyer, next: bluepeak.next, evidence: bluepeak.evidence, monitor: bluepeak.monitor }, { buyer: true, next: true, evidence: true, monitor: true });
  assert.equal(dashboard.signals[0].account, "Northstar Robotics");
});
