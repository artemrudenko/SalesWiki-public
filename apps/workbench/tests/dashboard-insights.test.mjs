import assert from "node:assert/strict";
import test from "node:test";

import { accounts } from "../src/data.js";
import { buildFixtureDashboard, formatObservationRange } from "../src/dashboardInsights.js";

test("fixture dashboard derives coverage, risk movement and dated signals from visible graph records", () => {
  const dashboard = buildFixtureDashboard(accounts.slice(0, 3), { "demo-company-bluepeak-energy": { topics: ["News"] } });
  assert.equal(dashboard.risk.length, 3);
  const atlasRisk = dashboard.risk.find((item) => item.name === "Atlas Foods");
  assert.ok(atlasRisk && atlasRisk.delta < 0);
  assert.equal(atlasRisk.needsReview, true, "stale account scores must not be presented as current");
  assert.deepEqual(atlasRisk.historyDates, ["2026-08-23", "2026-08-25", "2026-08-27", "2026-08-29"]);
  assert.equal(atlasRisk.periodLabel, "23–29 Aug 2026");
  assert.equal(atlasRisk.history.at(-1), atlasRisk.score, "latest synthetic point matches the recorded historical score");
  assert.equal(atlasRisk.delta, -4);
  const bluepeak = dashboard.coverage.find((item) => item.id === "demo-company-bluepeak-energy");
  assert.deepEqual({ buyer: bluepeak.buyer, next: bluepeak.next, evidence: bluepeak.evidence, monitor: bluepeak.monitor }, { buyer: true, next: true, evidence: true, monitor: true });
  assert.equal(dashboard.signals[0].account, "Northstar Robotics");
});

test("dashboard signal fixtures have an explicit synthetic period and remain role-scoped", () => {
  const dashboard = buildFixtureDashboard(accounts.slice(0, 3));
  assert.equal(dashboard.risk.length, 3);
  for (const item of dashboard.risk) {
    assert.equal(item.history.length, 4);
    assert.equal(item.historyDates.length, item.history.length);
    assert.ok(item.historyDates.every((date, index, dates) => !index || date > dates[index - 1]));
  }
});

test("observation date labels stay compact across and within months", () => {
  assert.equal(formatObservationRange(["2026-08-23", "2026-08-29"]), "Aug 23–29");
  assert.equal(formatObservationRange(["2026-08-30", "2026-09-02"]), "Aug 30–Sep 2, 2026");
});
