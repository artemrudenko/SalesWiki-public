import assert from "node:assert/strict";
import test from "node:test";

import { summarizePriorities } from "../src/prioritySummary.js";

test("priority summary separates actionable items from stale or unscored items", () => {
  assert.deepEqual(summarizePriorities([
    { score: 82 },
    { score: 71, needsReview: true },
    { score: "—" },
  ]), { total: 3, ready: 1, needsReview: 2 });
});

test("empty priority summary is explicit and stable", () => {
  assert.deepEqual(summarizePriorities([]), { total: 0, ready: 0, needsReview: 0 });
});
