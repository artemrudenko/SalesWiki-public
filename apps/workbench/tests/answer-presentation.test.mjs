import assert from "node:assert/strict";
import test from "node:test";

import { answerPresentation, citationLabel } from "../src/answerPresentation.js";

test("answer presentation retains freshness, gaps, next action and citations", () => {
  const card = answerPresentation({
    title: "Deal risk",
    conclusion: "Finance approval is not recorded.",
    freshness: "mixed",
    as_of: "2026-08-29",
    confidence: "medium",
    missing: ["No confirmed finance meeting date"],
    next_action: "Ask the owner to confirm the meeting date.",
    sections: [{ heading: "Known context", bullets: ["The champion is engaged."] }],
    citations: [{ title: "Discovery call", date: "2026-08-21" }],
  });

  assert.equal(card.freshness, "mixed");
  assert.equal(card.asOf, "2026-08-29");
  assert.deepEqual(card.missing, ["No confirmed finance meeting date"]);
  assert.equal(card.nextAction, "Ask the owner to confirm the meeting date.");
  assert.equal(card.sections[0].heading, "Known context");
  assert.equal(card.citations[0].title, "Discovery call");
});

test("an empty missing list differs from a missing Answer Contract field", () => {
  assert.deepEqual(answerPresentation({ missing: [] }).missing, []);
  assert.equal(answerPresentation({}).missing, null);
});

test("Answer Contract citations stay identifiable with or without a source path", () => {
  assert.equal(citationLabel({ boundary: "internal" }), "internal");
  assert.equal(citationLabel({ boundary: "sales-confidential", path: "wiki/Deal.md" }), "wiki/Deal.md");
});
