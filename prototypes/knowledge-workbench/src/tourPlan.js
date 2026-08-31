const roleLabels = {
  "sales-owner": "Account executive", sales: "Sales", hos: "Head of sales", revops: "Revenue operations", curator: "Knowledge curator", marketing: "Marketing", admin: "Administrator",
};
// The workbench routes by stable entity id, not by the readable fixture slug.
// Keeping those distinct prevents a tour step from landing in the app's
// deliberate "not found" state after a role change.
const tourAccountByRole = {
  "sales-owner": "demo-company-bluepeak-energy",
  sales: "demo-company-atlas-foods",
  marketing: "demo-company-atlas-foods",
};
const tourAccount = (role) => tourAccountByRole[role] ?? "demo-company-bluepeak-energy";

export function roleLabel(role) { return roleLabels[role] ?? role; }

const roleSteps = (role) => [
  { id: "today", target: "today-queue", role, view: "today", title: "Start with a role-specific day", body: `Today is not a generic dashboard. ${roleLabel(role)} sees only permitted priorities, evidence and account context.`, why: "It turns a large knowledge base into a short, safe next-action queue." },
  { id: "dashboard", target: "decision-signals", role, view: "today", title: "Read decision signals, not vanity metrics", body: "The dashboard turns only permitted, dated demo facts into risk movement, account readiness and the newest signals. It is not a forecast.", why: "You can see what changed and where context is missing before opening an account." },
  { id: "search", target: "safe-search", role, view: "today", title: "Search stays inside the access boundary", body: "Company search returns accessible accounts only. It never turns a partial name into a hint that a protected record exists.", why: "A safe product protects both the contents of data and its discoverability." },
  { id: "explore", target: "account-switcher", role, view: "explore", accountId: tourAccount(role), title: "Open an account, not a black box", body: "The explorer keeps relationships, evidence and decision context together. The graph is a navigation aid; every conclusion remains tied to a dated source.", why: "A rep can understand why an account is on the list before acting." },
  { id: "graph", target: "graph", role, view: "explore", accountId: tourAccount(role), title: "Explore the account in one connected view", body: "People, activity, commercial context and source-backed claims are arranged as a one-hop graph around the permitted account.", why: "Relationship context is easier to understand when it is visible without becoming an unbounded data dump." },
  { id: "evidence", target: "evidence", role, view: "explore", accountId: tourAccount(role), title: "Trace every conclusion back to evidence", body: "The evidence trace links the current decision context to dated source records. Selecting one focuses the same source in the graph and detail panel.", why: "The team can verify a recommendation instead of treating it as an opaque AI answer." },
  { id: "graph-controls", target: "graph-controls", role, view: "explore", accountId: tourAccount(role), title: "Inspect the graph without losing the recommended layout", body: "Filters narrow the view by knowledge type. Nodes can be moved for investigation, and Reset layout returns the reusable safe arrangement.", why: "The graph remains readable as accounts gain more people and activity." },
  { id: "assistant", target: "assistant", role, view: "explore", accountId: tourAccount(role), panel: "assistant", title: "Ask a bounded, cited question", body: "The assistant offers focused questions instead of free-form chat. It answers only from data available to this role and returns its citations.", why: "Useful AI should be inspectable and respect the same access boundary as the rest of the product." },
  { id: "monitoring", target: "monitoring-plan", role, view: "explore", accountId: tourAccount(role), panel: "monitor", title: "Configure the signals worth revisiting", body: "The monitoring screen makes a review cadence and signal scope explicit. In this demo it saves only a local browser preference; it does not start a vendor connection or notifications.", why: "A future monitor should be intentional, scoped and explainable — not an uncontrolled background scraper." },
  { id: "import", target: "import-draft", role, view: "explore", accountId: tourAccount(role), panel: "import", title: "Bring new context in as a controlled draft", body: "Import previews structured suggestions and sends a concise proposal to review. It does not write a card directly or retain the pasted source text in the vault.", why: "People can contribute useful context without bypassing evidence and approval controls." },
];

export function buildTourSteps({ mode, role }) {
  if (mode === "full") {
    const salesSteps = roleSteps("sales-owner");
    const marketingSteps = roleSteps("marketing");
    return [
      salesSteps[0], salesSteps[1],
      { id: "role-contrast", target: "persona-switcher", role: "marketing", view: "today", title: "The same workspace changes with the person", body: "Switching the synthetic person changes their Today queue, accessible accounts and decision-signal cards. It is a visible demonstration of a server-owned boundary.", why: "A role is not just a label that hides buttons; it changes what can be retrieved." },
      // Keep the rest of the product route in the marketing boundary. It makes
      // the role contrast tangible and avoids a distracting mid-tour switch
      // back to an account that marketing is not allowed to inspect.
      ...marketingSteps.slice(2),
      { id: "review", target: "review", role: "curator", view: "review", title: "Changes enter a governed review loop", body: "A curator can inspect proposals and record an explicit decision. Approval does not directly rewrite the knowledge base; a separate worker applies approved changes later.", why: "This preserves evidence, accountability and a clean audit trail." },
    ];
  }
  const steps = roleSteps(role);
  if (["curator", "hos", "revops", "admin"].includes(role)) steps.push({ id: "review", target: "review", role, view: "review", title: "Review is available to this role", body: "This role can inspect the governed queue. Depending on its authority it may inspect, approve or send a proposal back for clarification.", why: "The interface shows only workflows this person can actually use." });
  return steps;
}
