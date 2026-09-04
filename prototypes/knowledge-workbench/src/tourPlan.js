const roleLabels = {
  "sales-owner": "Account executive", sales: "Sales", hos: "Head of sales", revops: "Revenue operations", curator: "Knowledge curator", marketing: "Marketing", admin: "Administrator",
};

// The workbench routes by stable entity id, not by the readable fixture slug.
const tourAccountByRole = {
  "sales-owner": "demo-company-bluepeak-energy",
  sales: "demo-company-atlas-foods",
  marketing: "demo-company-atlas-foods",
};
const tourAccount = (role) => tourAccountByRole[role] ?? "demo-company-bluepeak-energy";

export function roleLabel(role) { return roleLabels[role] ?? role; }

const baseSteps = (role) => [
  { id: "today", target: "today-queue", role, view: "today", title: "Start with shared knowledge, shaped for one role", body: `Linked company, person, activity and source cards feed this queue. ${roleLabel(role)} sees only the permitted decisions and next actions.`, why: "The team maintains one knowledge model instead of rebuilding the same account context in separate notes." },
  { id: "dashboard", target: "decision-signals", role, view: "today", title: "Check whether the decision has enough context", body: "The dashboard turns only permitted, dated demo facts into risk movement, account readiness and the newest signals. It is not a forecast.", why: "A recommendation is useful only when the team can see what changed and what is still missing." },
  { id: "search", target: "safe-search", mobileTarget: "today-queue", role, view: "today", title: "Search stays inside the access boundary", body: "Company search returns accessible accounts only. It never turns a partial name into a hint that a protected record exists.", why: "A safe product protects both the contents of data and its discoverability." },
  { id: "explore", target: "account-switcher", role, view: "explore", accountId: tourAccount(role), title: "Open the context behind the decision", body: "The explorer keeps relationships, evidence and decision context together. The graph is a navigation aid; every conclusion remains tied to a dated source.", why: "A person can understand why an account is on the list before choosing an action." },
  { id: "graph", target: "graph", role, view: "explore", accountId: tourAccount(role), title: "Navigate linked cards, not another document pile", body: "Reusable cards for people, activity, commercial context and source-backed claims form a one-hop map around the permitted account.", why: "The same relationship can support sales and marketing without each team keeping its own copy." },
  { id: "evidence", target: "evidence", role, view: "explore", accountId: tourAccount(role), title: "Keep evidence stable while conclusions change", body: "The evidence trace links the current decision context to dated source records. Sources are preserved; compiled cards and conclusions can change through a governed path.", why: "The team can revisit an earlier decision without losing the material that supported it." },
  { id: "graph-controls", target: "graph-controls", role, view: "explore", accountId: tourAccount(role), title: "Inspect the graph without losing the recommended layout", body: "Filters narrow the view by knowledge type. Nodes can be moved for investigation, and Reset layout returns the reusable safe arrangement.", why: "The graph remains readable as accounts gain more people and activity." },
  { id: "assistant", target: "assistant", role, view: "explore", accountId: tourAccount(role), panel: "assistant", title: "Turn evidence into a next step you can inspect", body: "The assistant offers role-relevant questions instead of free-form chat. It narrows the options using permitted context and returns the citations behind its answer.", why: "The system supports the decision; the person can still challenge the evidence and choose the action." },
  { id: "monitoring", target: "monitoring-plan", role, view: "explore", accountId: tourAccount(role), panel: "monitor", title: "Configure the signals worth revisiting", body: "The monitoring screen makes a review cadence and signal scope explicit. In this demo it saves only a local browser preference; it does not start a vendor connection or notifications.", why: "A future monitor should be intentional, scoped and explainable — not an uncontrolled background scraper." },
  { id: "import", target: "import-draft", role, view: "explore", accountId: tourAccount(role), panel: "import", title: "Bring new context in as a controlled draft", body: "Import previews structured suggestions and sends a concise proposal to review. It does not write a card directly or retain the pasted source text in the vault.", why: "People can contribute useful context without bypassing evidence and approval controls." },
];

const reviewStep = (role, full = false) => ({
  id: "review", target: "review", role, view: "review",
  title: full ? "Changes enter a governed review loop" : "Review is available to this role",
  body: full
    ? "A curator can inspect proposals and record an explicit decision. Approval does not directly rewrite the knowledge base; a separate worker applies approved changes later."
    : "This role can inspect the governed queue. Depending on its authority it may inspect, approve or send a proposal back for clarification.",
  why: full ? "This preserves the proposed change, the review decision and the path into shared knowledge." : "The interface shows only workflows this person can actually use.",
});

const roleStepIds = {
  "sales-owner": ["today", "dashboard", "explore", "evidence", "assistant", "monitoring"],
  sales: ["today", "search", "explore", "evidence", "assistant", "import"],
  marketing: ["today", "dashboard", "explore", "evidence", "assistant", "import"],
  curator: ["today", "search", "explore", "evidence", "import"],
  hos: ["today", "dashboard", "search", "explore", "evidence"],
  revops: ["today", "dashboard", "search", "explore", "evidence"],
  admin: ["today", "search", "explore", "evidence", "import"],
};

const roleSteps = (role) => {
  const ids = roleStepIds[role] ?? ["today", "explore", "evidence", "assistant"];
  const steps = baseSteps(role).filter((step) => ids.includes(step.id));
  if (["curator", "hos", "revops", "admin"].includes(role)) steps.push(reviewStep(role));
  return steps;
};

const roleContrastStep = {
  id: "role-contrast", target: "persona-switcher", mobileTarget: "today-queue", role: "marketing", view: "today",
  title: "The same evidence supports a different decision",
  body: "Switching from Ethan in sales to Olivia in marketing changes the Today queue from account actions to campaign and message decisions, along with the context each role may retrieve.",
  why: "A useful shared knowledge base shapes the answer around the person's job and access boundary.",
};

export function buildTourSteps({ mode, role }) {
  if (mode === "quick") {
    const salesSteps = baseSteps("sales-owner");
    const marketingSteps = baseSteps("marketing");
    return [
      salesSteps[0],
      roleContrastStep,
      { ...marketingSteps.find((step) => step.id === "graph"), title: "Use the same account map for a marketing decision", body: "Olivia navigates the shared Atlas cards, connecting the audit signal, audience context and reusable proof without opening sales-confidential deal detail." },
      marketingSteps.find((step) => step.id === "evidence"),
      { ...marketingSteps.find((step) => step.id === "assistant"), title: "Ask what marketing should do next" },
      reviewStep("curator", true),
    ];
  }
  if (mode === "full") {
    const salesSteps = baseSteps("sales-owner");
    const marketingSteps = baseSteps("marketing");
    return [
      salesSteps[0], salesSteps[1], roleContrastStep,
      // Keep the rest of the route in the marketing boundary so the contrast
      // stays visible without switching back to a protected sales account.
      ...marketingSteps.slice(2),
      reviewStep("curator", true),
    ];
  }
  return roleSteps(role);
}
