import assert from "node:assert/strict";
import test from "node:test";
import { buildTourSteps, roleLabel } from "../src/tourPlan.js";

test("full tour covers the product journey and ends in governed review", () => {
  const steps = buildTourSteps({ mode: "full", role: "sales-owner" });
  assert.deepEqual(steps.map((step) => step.id), ["today", "dashboard", "role-contrast", "search", "explore", "graph", "evidence", "graph-controls", "assistant", "monitoring", "import", "review"]);
  assert.equal(steps[2].role, "marketing");
  assert.equal(steps.at(-1).role, "curator");
});

test("role tour includes review only for roles permitted to inspect it", () => {
  assert.equal(buildTourSteps({ mode: "role", role: "sales-owner" }).some((step) => step.id === "review"), false);
  assert.equal(buildTourSteps({ mode: "role", role: "curator" }).at(-1).id, "review");
  assert.equal(buildTourSteps({ mode: "role", role: "sales-owner" }).length, 10);
  assert.equal(buildTourSteps({ mode: "role", role: "marketing" }).find((step) => step.id === "explore").accountId, "atlas");
  assert.equal(roleLabel("curator"), "Knowledge curator");
});
