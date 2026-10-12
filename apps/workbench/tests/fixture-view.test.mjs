import assert from "node:assert/strict";
import test from "node:test";
import { accounts } from "../src/data.js";
import { shapeFixtureAccount, fixtureCanSeeCommercial } from "../src/fixtureView.js";
import { buildFixtureDashboard } from "../src/dashboardInsights.js";

const atlas = accounts.find((account) => account.id === "demo-company-atlas-foods");

test("marketing fixture graph and citations omit commercial details", () => {
  const view = shapeFixtureAccount(atlas, "marketing");
  const output = JSON.stringify(view);
  for (const secret of ["$160k", "Atlas Pilot", "FoodChain Systems", "Vendor Comparison", "SRC-050901"]) assert.equal(output.includes(secret), false, secret);
  assert.equal(view.sources.length, 2);
  const visible = new Set(view.nodes.map((node) => node.id));
  assert.ok(view.edges.every((edge) => visible.has(edge.source) && visible.has(edge.target)));
  const references = new Set(view.sources.map((source) => source.id));
  assert.ok(view.nodes.every((node) => node.data.evidenceIds.every((id) => references.has(id))));
  assert.equal(view.reviewStatus, atlas.reviewStatus);
  assert.equal(view.temperature, atlas.temperature);
});

test("role shaping is reversible and never mutates shared fixture evidence", () => {
  const before = JSON.stringify(atlas);
  shapeFixtureAccount(atlas, "marketing");
  const salesView = shapeFixtureAccount(atlas, "sales-owner");
  assert.ok(salesView.nodes.some((node) => node.data.kind === "deal"));
  assert.equal(JSON.stringify(atlas), before);
});

test("a narrow sales fixture sees commercial detail only for its assigned account", () => {
  assert.equal(fixtureCanSeeCommercial(atlas.id, "sales"), false);
  assert.equal(fixtureCanSeeCommercial("demo-company-northstar-robotics", "sales"), true);
  assert.equal(fixtureCanSeeCommercial(atlas.id, "unknown"), false);
});

test("marketing signal timeline uses the same shaped sources as its graph", () => {
  const shaped = accounts.map((account) => shapeFixtureAccount(account, "marketing"));
  const dashboard = buildFixtureDashboard(shaped);
  const privateLabels = accounts.flatMap((account) => account.sources.filter((source) => source.boundary === "sales-confidential").map((source) => source.short));
  assert.ok(dashboard.signals.every((signal) => !privateLabels.includes(signal.title)));
});
