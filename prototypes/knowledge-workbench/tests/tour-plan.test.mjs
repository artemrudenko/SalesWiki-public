import assert from "node:assert/strict";
import test from "node:test";
import { buildTourSteps, roleLabel } from "../src/tourPlan.js";

test("quick tour proves the operating loop in six steps", () => {
  const steps = buildTourSteps({ mode: "quick", role: "sales-owner" });
  assert.deepEqual(steps.map((step) => step.id), ["today", "role-contrast", "graph", "evidence", "assistant", "review"]);
  assert.equal(steps[1].role, "marketing");
  assert.equal(steps.at(-1).role, "curator");
});

test("full tour covers the product journey and ends in governed review", () => {
  const steps = buildTourSteps({ mode: "full", role: "sales-owner" });
  assert.deepEqual(steps.map((step) => step.id), ["today", "dashboard", "role-contrast", "search", "explore", "graph", "evidence", "graph-controls", "assistant", "monitoring", "import", "review"]);
  assert.equal(steps[2].role, "marketing");
  assert.equal(steps.find((step) => step.id === "explore").accountId, "demo-company-atlas-foods");
  assert.equal(steps.at(-1).role, "curator");
});

test("role tour includes review only for roles permitted to inspect it", () => {
  assert.equal(buildTourSteps({ mode: "role", role: "sales-owner" }).some((step) => step.id === "review"), false);
  assert.equal(buildTourSteps({ mode: "role", role: "curator" }).at(-1).id, "review");
  assert.deepEqual(buildTourSteps({ mode: "role", role: "sales-owner" }).map((step) => step.id), ["today", "dashboard", "explore", "evidence", "assistant", "monitoring"]);
  assert.deepEqual(buildTourSteps({ mode: "role", role: "marketing" }).map((step) => step.id), ["today", "dashboard", "search", "explore", "evidence", "import"]);
  assert.deepEqual(buildTourSteps({ mode: "role", role: "curator" }).map((step) => step.id), ["today", "search", "explore", "evidence", "import", "review"]);
  assert.equal(buildTourSteps({ mode: "role", role: "marketing" }).find((step) => step.id === "explore").accountId, "demo-company-atlas-foods");
  assert.equal(roleLabel("curator"), "Knowledge curator");
});
