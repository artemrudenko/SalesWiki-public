import assert from "node:assert/strict";
import test from "node:test";

import { accounts } from "../src/data.js";
import { adaptGraphView } from "../src/graphAdapter.js";

function fixture() {
  return {
    contract: "saleswiki.graph-view",
    version: 1,
    root_id: "company:fourth",
    access: "sanitized",
    summary: {
      title: "Fourth Company",
      conclusion: "A differently shaped account still uses the same adapter.",
      confidence: "high",
      freshness: "fresh",
      as_of: "2026-08-29",
      next_action: "Confirm the pilot owner.",
      score: 81,
    },
    nodes: [
      { id: "company:fourth", type: "company", label: "Fourth Company", subtitle: "Target account", detail: "Root", metadata: { code: "COMP-4", owner: "Owner" }, evidence_ids: ["e1"] },
      { id: "person:one", type: "person", label: "Champion", subtitle: "Operations", detail: "First person", metadata: {}, evidence_ids: ["e1"] },
      { id: "person:two", type: "person", label: "Buyer", subtitle: "Finance", detail: "Second person", metadata: {}, evidence_ids: ["e1"] },
      { id: "deal:one", type: "deal", label: "Pilot", subtitle: "Discovery", detail: "Deal", metadata: { owner: "Owner" }, evidence_ids: ["e1"] },
      { id: "lead:one", type: "lead", label: "Expansion lead", subtitle: "Qualified", detail: "Lead", metadata: { owner: "Owner" }, evidence_ids: ["e1"] },
      { id: "competitor:one", type: "competitor", label: "Alternative", subtitle: "Competitor", detail: "Risk", metadata: {}, evidence_ids: ["e1"] },
      { id: "source:one", type: "source", label: "Call", subtitle: "Today", detail: "Evidence", metadata: {}, evidence_ids: ["e1"] }
    ],
    edges: [
      { id: "edge:person:one", type: "PERSON_WORKS_AT_COMPANY", from: "person:one", to: "company:fourth", label: "", evidence_ids: ["e1"] },
      { id: "edge:person:two", type: "PERSON_WORKS_AT_COMPANY", from: "person:two", to: "company:fourth", label: "", evidence_ids: ["e1"] },
      { id: "edge:deal", type: "DEAL_WITH_COMPANY", from: "company:fourth", to: "deal:one", label: "", evidence_ids: ["e1"] },
      { id: "edge:source", type: "RELATED_TO", from: "source:one", to: "company:fourth", label: "EVIDENCE FOR", evidence_ids: ["e1"] }
    ],
    evidence: [
      { id: "e1", title: "Call", status: "verified", as_of: "2026-08-29", summary: "Evidence", citation: { boundary: "internal", path: "raw/calls/fourth.md" } }
    ],
    restricted: ["One related record is restricted."],
    missing: []
  };
}

test("one reusable adapter lays out a differently shaped fourth company", () => {
  const view = fixture();
  const account = adaptGraphView(view);
  assert.equal(account.name, "Fourth Company");
  assert.equal(account.nodes.length, 7);
  const root = account.nodes.find((node) => node.id === view.root_id);
  assert.deepEqual(root.position, { x: 460, y: 240 });
  assert.equal(root.data.detail, view.summary.conclusion, "root decision summary comes from GraphView summary");
  const people = account.nodes.filter((node) => node.data.kind === "person");
  assert.equal(new Set(people.map((node) => node.position.x)).size, 2, "people share a lane without overlapping");
  assert.ok(Math.abs(people[0].position.x - people[1].position.x) >= 320, "cards keep a readable horizontal gutter");
  const commercial = account.nodes.filter((node) => ["deal", "lead"].includes(node.data.kind));
  assert.ok(commercial.every((node) => node.position.x < root.position.x), "commercial context stays on the left");
  assert.ok(Math.abs(commercial[0].position.y - commercial[1].position.y) >= 150, "same-side types use a readable vertical stack");
  const competitor = account.nodes.find((node) => node.data.kind === "competitor");
  assert.ok(competitor.position.x > root.position.x, "market context stays on the right");
  const source = account.nodes.find((node) => node.data.kind === "source");
  assert.ok(source.position.y - root.position.y >= 340, "lower lanes leave room for edges and labels");
  assert.ok(view.nodes.every((node) => !("position" in node)), "MCP contract remains layout-neutral");
});

test("BluePeak demo shows a buying committee and multiple activities without overlap", () => {
  const bluePeak = accounts.find((account) => account.id === "demo-company-bluepeak-energy");
  const people = bluePeak.nodes.filter((node) => node.data.kind === "person");
  const activity = bluePeak.nodes.filter((node) => ["call", "task"].includes(node.data.kind));

  assert.equal(people.length, 3, "demo includes champion, economic buyer, and technical evaluator");
  assert.equal(activity.length, 3, "demo includes original call plus follow-up activity and next step");
  assert.equal(new Set(people.map((node) => `${node.position.x}:${node.position.y}`)).size, people.length, "contact nodes occupy separate positions");
  assert.equal(new Set(activity.map((node) => `${node.position.x}:${node.position.y}`)).size, activity.length, "activity nodes occupy separate positions");
});

test("adapter fails closed on a dangling edge", () => {
  const view = fixture();
  view.edges.push({ id: "bad", type: "RELATED_TO", from: "hidden:deal", to: view.root_id, label: "", evidence_ids: [] });
  assert.throws(() => adaptGraphView(view), /hidden or missing endpoint/);
});

test("adapter fails closed on missing evidence", () => {
  const view = fixture();
  view.nodes[0].evidence_ids = ["not-present"];
  assert.throws(() => adaptGraphView(view), /missing evidence/);
});
