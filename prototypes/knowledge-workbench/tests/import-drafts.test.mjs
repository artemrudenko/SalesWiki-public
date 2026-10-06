import assert from "node:assert/strict";
import test from "node:test";
import { createImportDrafts, summarizeImportDrafts } from "../src/importDrafts.js";

test("CSV becomes explicit company, lead and next-step drafts", () => {
  const drafts = createImportDrafts({ source: "csv", accountName: "Acme", text: "Company,Contact,Next step\nAcme,Ada Lovelace,Send proposal" });
  assert.deepEqual(drafts.map(({ kind, title, state }) => ({ kind, title, state })), [
    { kind: "company", title: "Acme", state: "ready" },
    { kind: "lead", title: "Ada Lovelace", state: "ready" },
    { kind: "next-step", title: "Send proposal", state: "ready" },
  ]);
});

test("a mismatched company is held for human matching", () => {
  const drafts = createImportDrafts({ source: "notes", accountName: "Acme", text: "Company: Other Corp\nNext step: Call on Friday" });
  assert.equal(drafts[0].state, "needs-match");
  assert.equal(drafts[1].state, "ready");
});

test("review summary excludes unresolved items and limits the transport payload", () => {
  const summary = summarizeImportDrafts([
    { kind: "company", title: "Acme", state: "ready" },
    { kind: "lead", title: "Private", state: "needs-match" },
  ], "Acme");
  assert.match(summary, /company: Acme/);
  assert.doesNotMatch(summary, /Private/);
  assert.ok(summary.length <= 480);
});
