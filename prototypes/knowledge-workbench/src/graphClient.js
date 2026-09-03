export const graphDemoScenarios = [
  { value: "ready", label: "Ready" },
  { value: "loading", label: "Loading" },
  { value: "blocked", label: "Access blocked" },
  { value: "not-found", label: "Not found" },
  { value: "ambiguous", label: "Ambiguous match" },
  { value: "stale", label: "Stale data" },
  { value: "truncated", label: "Truncated graph" },
  { value: "contract-error", label: "Contract error" },
];

const result = (status, extra = {}) => ({ status, ...extra });

const fixturePersonas = [
  { id: "demo-ethan-ae", name: "Ethan AE", role: "sales-owner", team: "sales-west" },
  { id: "demo-sam-sdr", name: "Sam SDR", role: "sales", team: "sales-west" },
  { id: "demo-claire-hos", name: "Claire HoS", role: "hos", team: "sales" },
  { id: "demo-raj-revops", name: "Raj RevOps", role: "revops", team: "revops" },
  { id: "demo-sophie-curator", name: "Sophie Curator", role: "curator", team: "knowledge" },
  { id: "demo-olivia-marketing", name: "Olivia Marketing", role: "marketing", team: "marketing" },
  { id: "demo-ada-admin", name: "Ada Admin", role: "admin", team: "ops" },
];
let fixturePerson = fixturePersonas[0];
let fixtureProposalNumber = 50;
let fixtureProposals = [
  { proposal_id: "proposal-0042", status: "draft", type: "ingest_resource", target: "bluepeak", note: "Workbench draft import for BluePeak Energy.", requester: "demo-ethan-ae", role: "sales", created: "2026-08-30T09:15:00Z" },
  { proposal_id: "proposal-0041", status: "draft", type: "flag_stale_or_wrong", target: "atlas", note: "Confirm the proposed technical-validation date before the next call.", requester: "demo-ethan-ae", role: "sales", created: "2026-08-30T08:40:00Z" },
];
const fixtureAccountVisibility = {
  "sales-owner": ["bluepeak", "atlas", "summit-grid"],
  sales: ["atlas", "northstar"],
  marketing: ["atlas", "northstar", "summit-grid"],
};

const fixtureRoleProfiles = {
  "sales-owner": {
    label: "Account executive", eyebrow: "Owned opportunity queue", showRisk: true,
    focus: "Move your active opportunities", riskTitle: "Owned deal momentum", coverageTitle: "Account readiness", signalTitle: "Newest account evidence",
    conclusion: "Focus on the accounts you own: protect the next step, bring in the right buyer, and make the commercial case measurable.",
    actions: [
      ["bluepeak", "Confirm finance workshop", "The economic buyer still needs a clear ROI case.", "Book the workshop before commercial terms."],
      ["summit-grid", "Align executive review", "The expansion has a dated decision window.", "Confirm the 30-day outcome and executive owner."],
      ["atlas", "Make the audit pilot measurable", "Implementation speed is a live evaluation criterion.", "Send the evidence-gathering plan."],
    ],
  },
  sales: {
    label: "Sales development", eyebrow: "Pipeline creation queue", showRisk: true,
    focus: "Create qualified next conversations", riskTitle: "Qualification momentum", coverageTitle: "Discovery coverage", signalTitle: "Fresh outreach signals",
    conclusion: "Create qualified conversations where there is a timely signal, then hand over a sourced and explicit next step.",
    actions: [
      ["northstar", "Map the technical buying group", "Automation expansion is active and the champion is engaged.", "Identify the operations and finance stakeholders."],
      ["atlas", "Confirm the audit decision timeline", "The compliance trigger makes the problem concrete.", "Ask for the audit date and evaluation owner."],
    ],
  },
  hos: {
    label: "Head of Sales", eyebrow: "Team pipeline review", showRisk: true,
    focus: "Unblock the team’s highest-value work", riskTitle: "Team deal momentum", coverageTitle: "Team account readiness", signalTitle: "Signals requiring leadership attention",
    conclusion: "Look across the team: remove blockers on active deals and intervene where the next step or buying coverage is weak.",
    actions: [
      ["atlas", "Unblock the compliance evaluation", "Score movement is negative and the next step needs ownership.", "Review the pilot plan with the account owner."],
      ["summit-grid", "Protect the expansion decision", "The executive review is the near-term commercial gate.", "Confirm sponsor coverage and decision timing."],
      ["northstar", "Check pilot proof", "Technical validation is strong but proof needs to stay measurable.", "Review the baseline and success criteria."],
    ],
  },
  revops: {
    label: "Revenue operations", eyebrow: "Pipeline quality queue", showRisk: true,
    focus: "Improve pipeline quality before reporting", riskTitle: "Score movement to validate", coverageTitle: "Data completeness", signalTitle: "Newest data to reconcile",
    conclusion: "Improve the quality of the operating picture: resolve missing next steps, confirm score movement and keep evidence linked to each change.",
    actions: [
      ["atlas", "Validate the score decline", "The account lost momentum across dated observations.", "Check the evaluation date and owner before reporting."],
      ["bluepeak", "Confirm buyer coverage", "Commercial progress depends on an economic-buyer conversation.", "Verify the finance contact and scheduled workshop."],
      ["summit-grid", "Check monitoring coverage", "A high-value expansion needs a maintained signal plan.", "Add or review the account monitor."],
    ],
  },
  curator: {
    label: "Knowledge curator", eyebrow: "Knowledge quality queue", showRisk: false,
    focus: "Keep decisions traceable and reviewable", riskTitle: "", coverageTitle: "Evidence completeness", signalTitle: "Evidence needing review",
    conclusion: "Prioritise knowledge quality: verify claims that influence decisions, resolve review-needed sources and keep the proposal queue moving.",
    actions: [
      ["bluepeak", "Review competitor evidence", "Competitor Intel is still marked Needs review.", "Verify or return the cited source."],
      ["atlas", "Resolve vendor comparison", "A decision-relevant source is waiting for review.", "Check provenance and update the confidence."],
      ["northstar", "Validate pilot proof source", "Technical evidence supports an active decision.", "Confirm date, source and allowed audience."],
    ],
  },
  marketing: {
    label: "Marketing", eyebrow: "Market activation queue", showRisk: false,
    focus: "Turn permitted signals into relevant messages", riskTitle: "", coverageTitle: "Audience context", signalTitle: "New market signals",
    conclusion: "Use only the broad, permitted account context to prepare relevant messages and flag missing or sensitive context for review.",
    actions: [
      ["northstar", "Create an automation proof angle", "Expansion signals point to changeover-time outcomes.", "Draft a measurable proof message."],
      ["atlas", "Build a compliance audience", "Audit evidence gathering is an explicit problem.", "Prepare a compliant campaign segment."],
      ["summit-grid", "Plan the executive message", "The account is approaching an executive review.", "Create a reusable ROI narrative without deal detail."],
    ],
  },
  admin: {
    label: "Workspace administrator", eyebrow: "Governance queue", showRisk: false,
    focus: "Keep the workspace safe and operable", riskTitle: "", coverageTitle: "Workspace coverage", signalTitle: "Recent governed activity",
    conclusion: "Maintain safe operations: inspect the review queue, verify boundaries and make sure the demo workspace remains reproducible.",
    actions: [
      ["bluepeak", "Check access boundary", "The account includes a protected personal-data handle.", "Confirm the displayed boundary is correct."],
      ["atlas", "Review pending correction", "A dated technical-validation detail needs a decision.", "Open the governed review queue."],
      ["summit-grid", "Check monitor configuration", "The account has an active expansion signal.", "Confirm its monitor is scoped and documented."],
    ],
  },
};

export const getFixtureRoleProfile = (role) => fixtureRoleProfiles[role] ?? fixtureRoleProfiles["sales-owner"];
export const isFixtureAccountVisible = (accountId, role) => {
  const allowed = fixtureAccountVisibility[role];
  const knownDemoAccount = Object.values(fixtureAccountVisibility).flat().some((value) => String(accountId).includes(value));
  return !allowed || !knownDemoAccount || allowed.some((value) => String(accountId).includes(value));
};
const canFixtureOpen = (accountId) => isFixtureAccountVisible(accountId, fixturePerson.role);
const canFixtureReview = () => ["curator", "hos", "revops", "admin"].includes(fixturePerson.role);
const canFixtureDecide = () => ["curator", "hos", "admin"].includes(fixturePerson.role);
const fixtureId = () => `proposal-${String(fixtureProposalNumber++).padStart(4, "0")}`;

function graphViewResult(graphView, adaptGraphView) {
  if (graphView?.contract !== "saleswiki.graph-view" || graphView?.version !== 1) {
    throw Object.assign(new Error("Unsupported GraphView contract"), { code: "GRAPH-CONTRACT-001" });
  }
  const access = graphView?.access;
  const emptyAccess = ["blocked", "not-found", "ambiguous", "aggregated"].includes(access);
  if (emptyAccess) {
    const collections = [graphView.nodes, graphView.edges, graphView.evidence];
    if (graphView.root_id !== null || collections.some((items) => !Array.isArray(items) || items.length > 0)) {
      throw Object.assign(new Error("Empty GraphView access state contains graph records"), { code: "GRAPH-EMPTY-001" });
    }
  }
  if (access === "blocked") {
    return result("blocked", {
      reason: graphView.summary?.conclusion ?? "This account is outside your current access boundary.",
      nextAction: graphView.summary?.next_action ?? "Request access.",
    });
  }
  if (access === "not-found") {
    return result("not-found", {
      message: graphView.summary?.conclusion ?? "No company matched this identifier.",
    });
  }
  if (access === "ambiguous") {
    return result("ambiguous", {
      message: graphView.summary?.conclusion ?? "More than one company matched this request.",
      candidates: [],
    });
  }
  if (access === "aggregated") {
    return result("aggregated", {
      message: graphView.summary?.conclusion ?? "Only aggregated knowledge is available for this request.",
      nextAction: graphView.summary?.next_action ?? "Open an aggregate report.",
    });
  }
  if (access !== "allowed" && access !== "sanitized") {
    throw Object.assign(new Error("Unsupported GraphView access state"), { code: "GRAPH-ACCESS-001" });
  }
  return result("ready", { data: adaptGraphView(graphView), notices: [] });
}

function safeEndpoint(endpoint) {
  const value = String(endpoint ?? "").trim();
  if (!value) throw new Error("BFF graph client requires a public endpoint");

  const absolute = /^https?:\/\//i.test(value);
  const parsed = new URL(value, "http://saleswiki.local");
  if (!/^https?:$/.test(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error("Graph endpoint must be an HTTP(S) URL without credentials, query parameters, or fragments");
  }
  return absolute ? parsed.toString() : `${parsed.pathname}`;
}

function entityGraphUrl(endpoint, accountId) {
  const separator = endpoint.includes("?") ? "&" : "?";
  return `${endpoint}${separator}entity=${encodeURIComponent(accountId)}`;
}

function errorResult(error, fallbackCode) {
  return result("contract-error", {
    message: "SalesWiki could not safely render this graph response.",
    reference: error?.code ?? fallbackCode,
  });
}

export function createFixtureGraphClient({ accounts, latencyMs = 180 } = {}) {
  if (!Array.isArray(accounts) || accounts.length === 0) {
    throw new Error("Fixture graph client requires at least one account");
  }

  const wait = (signal) => {
    if (signal?.aborted) return Promise.reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
    if (latencyMs <= 0) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const timer = globalThis.setTimeout(resolve, latencyMs);
      signal?.addEventListener("abort", () => {
        globalThis.clearTimeout(timer);
        reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
      }, { once: true });
    });
  };

  return {
    source: "fixture",

    async listAccounts() {
      await wait();
      return accounts.map(({ id, name, code }) => ({ id, name, code }));
    },

    async getEntityGraph({ accountId, scenario = "ready", signal }) {
      if (scenario === "loading") return result("loading");
      await wait(signal);

      const account = accounts.find((item) => item.id === accountId);
      if (scenario === "blocked") {
        return result("blocked", {
          reason: "This account is outside your current access boundary.",
          nextAction: "Request access from the account owner or open a sanitized brief.",
        });
      }
      if (scenario === "not-found" || !account) {
        return result("not-found", {
          message: "No company matches this identifier in the current knowledge boundary.",
        });
      }
      if (!canFixtureOpen(accountId)) return result("blocked", { reason: "Marketing can use a broad account view here, but this sales-confidential account is not available.", nextAction: "Choose another account or request approved access." });
      if (scenario === "ambiguous") {
        return result("ambiguous", {
          message: "Several records may refer to this company. Choose the intended account.",
          candidates: accounts.slice(0, 3).map(({ id, name, code }) => ({ id, name, code })),
        });
      }
      if (scenario === "contract-error") {
        return result("contract-error", {
          message: "The graph response uses an unsupported contract version.",
          reference: "GRAPH-CONTRACT-001",
        });
      }

      const notices = [];
      if (scenario === "stale") {
        notices.push({
          kind: "stale",
          title: "Some account knowledge is stale",
          message: "The newest verified activity is outside the review window. Confirm the next step before acting.",
        });
      }
      if (scenario === "truncated") {
        notices.push({
          kind: "truncated",
          title: "Focused view",
          message: "This graph reached the one-hop display limit. Narrow the view or request another page to inspect more relationships.",
        });
      }
      return result("ready", { data: account, notices });
    },
  };
}

export function createMcpGraphClient({ invoke, adaptGraphView }) {
  if (typeof invoke !== "function" || typeof adaptGraphView !== "function") {
    throw new Error("MCP graph client requires invoke and adaptGraphView functions");
  }

  return {
    source: "mcp",
    async listAccounts() {
      return [];
    },
    async getEntityGraph({ accountId }) {
      try {
        const graphView = await invoke("saleswiki.entity_graph", {
          entity: accountId,
          entity_type: "company",
          depth: 1,
        });
        return graphViewResult(graphView, adaptGraphView);
      } catch (error) {
        return errorResult(error, "GRAPH-MCP-001");
      }
    },
  };
}

export function createBffGraphClient({ endpoint, adaptGraphView, fetchImpl = globalThis.fetch }) {
  if (typeof adaptGraphView !== "function" || typeof fetchImpl !== "function") {
    throw new Error("BFF graph client requires fetch and adaptGraphView functions");
  }
  const graphEndpoint = safeEndpoint(endpoint);

  return {
    source: "bff",
    async listAccounts() {
      return [];
    },
    async getEntityGraph({ accountId, signal }) {
      try {
        const response = await fetchImpl(entityGraphUrl(graphEndpoint, accountId), {
          method: "GET",
          headers: { Accept: "application/json" },
          credentials: "same-origin",
          signal,
        });
        if (!response?.ok) {
          throw Object.assign(new Error(`Graph endpoint returned HTTP ${response?.status ?? "unknown"}`), { code: "GRAPH-HTTP-001" });
        }
        const contentType = response.headers?.get?.("content-type") ?? "";
        if (!contentType.toLowerCase().includes("application/json")) {
          throw Object.assign(new Error("Graph endpoint did not return JSON"), { code: "GRAPH-JSON-001" });
        }
        const graphView = await response.json();
        if (!graphView || typeof graphView !== "object" || Array.isArray(graphView)) {
          throw Object.assign(new Error("Graph endpoint returned an invalid JSON body"), { code: "GRAPH-JSON-002" });
        }
        return graphViewResult(graphView, adaptGraphView);
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return errorResult(error, "GRAPH-BFF-001");
      }
    },
  };
}

export function createBffCompanySearchClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const searchEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/company-search");
  return {
    async search({ query, signal } = {}) {
      try {
        const response = await fetchImpl(`${searchEndpoint}?q=${encodeURIComponent(query)}`, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        const value = await response.json();
        if (!response.ok || !value || value.status !== "ok" || value.query !== query || !Array.isArray(value.items) || value.items.some((item) => !item || item.type !== "company" || typeof item.entity_id !== "string" || typeof item.label !== "string")) throw new Error("Invalid company search");
        return { status: "ready", items: value.items.map((item) => ({ id: item.entity_id, label: item.label, freshness: item.freshness ?? "" })) };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error", items: [] };
      }
    },
  };
}

export function createFixtureCompanySearchClient({ accounts }) {
  return {
    async search({ query } = {}) {
      const normalized = String(query ?? "").trim().toLowerCase();
      const items = accounts.filter((account) => canFixtureOpen(account.id) && `${account.name} ${account.code} ${account.id}`.toLowerCase().includes(normalized)).slice(0, 8).map((account) => ({ id: account.id, label: account.name, freshness: account.freshness }));
      return { status: "ready", items };
    },
  };
}

export function createBffDailyClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const dailyEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/my-day");
  return {
    async getMyDay({ signal } = {}) {
      try {
        const response = await fetchImpl(dailyEndpoint, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        if (!response?.ok) throw new Error("Daily endpoint returned an error");
        const value = await response.json();
        if (!value || typeof value !== "object" || !Array.isArray(value.sections) || typeof value.conclusion !== "string") throw new Error("Invalid daily answer");
        return { status: "ready", data: value };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createBffDashboardClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const dashboardEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/dashboard");
  return {
    async getDashboard({ signal } = {}) {
      try {
        const response = await fetchImpl(dashboardEndpoint, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        const value = await response.json();
        if (!response.ok || value?.contract !== "saleswiki.dashboard-view" || value?.version !== 1 || value?.access !== "allowed" || !Array.isArray(value.risk) || !Array.isArray(value.coverage) || !Array.isArray(value.signals)) throw new Error("Invalid dashboard");
        return {
          status: "ready",
          data: {
            risk: value.risk.map((item) => ({ id: item.entity_id, name: item.label, history: item.history, delta: item.delta, score: item.score })),
            coverage: value.coverage.map((item) => ({ id: item.entity_id, name: item.label, buyer: item.economic_buyer, next: item.next_step, evidence: item.verified_evidence, monitor: item.monitoring })),
            signals: value.signals.map((item) => ({ id: item.id, accountId: item.entity_id, account: item.account, title: item.title, date: item.as_of, status: item.freshness === "fresh" ? "Verified" : "Needs review" })),
            historyStatus: value.history_status,
            synthetic: value.synthetic,
          },
        };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createBffSessionClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const sessionEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/session");
  const personaEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/demo-persona");
  const validate = (value) => {
    if (!value || typeof value !== "object" || !value.person || typeof value.person.id !== "string" || typeof value.person.name !== "string" || typeof value.person.role !== "string" || !Array.isArray(value.personas) || typeof value.can_switch_persona !== "boolean" || typeof value.can_review !== "boolean") throw new Error("Invalid Workbench session");
    return value;
  };
  return {
    async getSession({ signal } = {}) {
      try {
        const response = await fetchImpl(sessionEndpoint, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        return response.ok ? { status: "ready", data: validate(await response.json()) } : { status: "error" };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
    async switchPersona(actorId, { signal } = {}) {
      try {
        const response = await fetchImpl(personaEndpoint, { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, credentials: "same-origin", signal, body: JSON.stringify({ actor_id: actorId }) });
        return response.ok ? { status: "ready", data: validate(await response.json()) } : { status: "error" };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createFixtureSessionClient() {
  const payload = () => ({ mode: "fixture", person: fixturePerson, personas: fixturePersonas, can_switch_persona: true, can_review: canFixtureReview() });
  return { async getSession() { return { status: "ready", data: payload() }; }, async switchPersona(actorId) { const next = fixturePersonas.find((item) => item.id === actorId); if (!next) return { status: "error" }; fixturePerson = next; return { status: "ready", data: payload() }; } };
}

export function createBffImportClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const importEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/import-proposal");
  return {
    async submit({ target, summary, signal }) {
      try {
        const response = await fetchImpl(importEndpoint, {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          credentials: "same-origin",
          signal,
          body: JSON.stringify({ target, summary }),
        });
        if (!response?.ok) throw new Error("Import endpoint returned an error");
        const value = await response.json();
        if (!value || value.status !== "draft" || typeof value.proposal_id !== "string") throw new Error("Invalid import proposal");
        return { status: "ready", proposalId: value.proposal_id };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createFixtureImportClient() {
  return { async submit({ target, summary }) { const proposalId = fixtureId(); fixtureProposals.unshift({ proposal_id: proposalId, status: "draft", type: "ingest_resource", target, note: summary, requester: fixturePerson.id, role: fixturePerson.role, created: new Date().toISOString() }); return { status: "ready", proposalId }; } };
}

export function createBffAccountBriefClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const briefEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/account-brief");
  return {
    async getBrief({ accountId, signal } = {}) {
      try {
        const response = await fetchImpl(`${briefEndpoint}?entity=${encodeURIComponent(accountId)}`, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        const value = await response.json();
        if (!response.ok || !value || typeof value.conclusion !== "string" || !Array.isArray(value.citations)) throw new Error("Invalid account brief");
        return { status: "ready", data: value };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createBffGuidedAnswerClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const guidedEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/guided-answer");
  return {
    async ask({ intent, accountId, signal } = {}) {
      try {
        const response = await fetchImpl(`${guidedEndpoint}?intent=${encodeURIComponent(intent)}&entity=${encodeURIComponent(accountId)}`, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        const value = await response.json();
        if (!response.ok || value?.intent !== intent || typeof value?.conclusion !== "string" || !Array.isArray(value?.citations)) throw new Error("Invalid guided answer");
        return { status: "ready", data: value };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createBffUpdateClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const updateEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/update-proposal");
  return {
    async submit({ target, note, signal } = {}) {
      try {
        const response = await fetchImpl(updateEndpoint, { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, credentials: "same-origin", signal, body: JSON.stringify({ target, note }) });
        const value = await response.json();
        if (!response.ok || value?.status !== "draft" || typeof value.proposal_id !== "string") throw new Error("Invalid update proposal");
        return { status: "ready", proposalId: value.proposal_id };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createFixtureAccountBriefClient({ accounts }) {
  return { async getBrief({ accountId }) { const account = accounts.find((item) => item.id === accountId); return account ? { status: "ready", data: { title: `Account brief: ${account.name}`, conclusion: account.conclusion, citations: account.sources, confidence: account.confidence, freshness: account.freshness, next_action: account.nextAction } } : { status: "error" }; } };
}

export function createFixtureGuidedAnswerClient({ accounts }) {
  return {
    async ask({ intent, accountId }) {
      const account = accounts.find((item) => item.id === accountId);
      if (!account || !canFixtureOpen(accountId)) return { status: "error" };
      const copy = {
        account_brief: ["Account brief", account.conclusion],
        what_changed: ["What changed", account.sources[0]?.summary ?? account.conclusion],
        next_step: ["Recommended next step", account.nextAction ?? "Confirm the next step with the account owner."],
        deal_risk: ["Deal risk", account.conclusion],
        call_prep: ["Call preparation", account.sources[1]?.summary ?? account.conclusion],
      }[intent];
      return copy ? { status: "ready", data: { intent, title: `${copy[0]}: ${account.name}`, conclusion: copy[1], citations: account.sources, confidence: account.confidence, freshness: account.freshness, next_action: account.nextAction } } : { status: "error" };
    },
  };
}

export function createFixtureUpdateClient() {
  return { async submit({ target, note }) { const proposalId = fixtureId(); fixtureProposals.unshift({ proposal_id: proposalId, status: "draft", type: "flag_stale_or_wrong", target, note, requester: fixturePerson.id, role: fixturePerson.role, created: new Date().toISOString() }); return { status: "ready", proposalId }; } };
}

export function createBffReviewClient({ endpoint, fetchImpl = globalThis.fetch }) {
  const graphEndpoint = safeEndpoint(endpoint);
  const queueEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/review-queue");
  const decisionEndpoint = graphEndpoint.replace(/\/entity-graph$/, "/review-proposal");
  return {
    async getQueue({ signal } = {}) {
      try {
        const response = await fetchImpl(queueEndpoint, { method: "GET", headers: { Accept: "application/json" }, credentials: "same-origin", signal });
        const value = await response.json();
        if (!response.ok || !value || !["allowed", "blocked"].includes(value.access) || !Array.isArray(value.items) || typeof value.can_decide !== "boolean") throw new Error("Invalid review queue");
        return { status: "ready", data: value };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
    async decide({ proposalId, action, reason = "", signal } = {}) {
      try {
        const response = await fetchImpl(decisionEndpoint, { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, credentials: "same-origin", signal, body: JSON.stringify({ proposal_id: proposalId, action, reason }) });
        const value = await response.json();
        if (!response.ok || !value || typeof value.status !== "string") throw new Error("Invalid review decision");
        return { status: "ready", data: value };
      } catch (error) {
        if (error?.name === "AbortError" || signal?.aborted) throw error;
        return { status: "error" };
      }
    },
  };
}

export function createFixtureReviewClient() {
  return {
    async getQueue() { return { status: "ready", data: canFixtureReview() ? { access: "allowed", can_decide: canFixtureDecide(), items: fixtureProposals.filter((item) => item.status !== "rejected") } : { access: "blocked", can_decide: false, items: [] } }; },
    async decide({ proposalId, action }) {
      if (!canFixtureDecide()) return { status: "error" };
      fixtureProposals = fixtureProposals.map((item) => item.proposal_id === proposalId ? { ...item, status: action === "approve" ? "approved" : "rejected" } : item);
      return { status: "ready", data: { proposal_id: proposalId, status: action === "approve" ? "approved" : "rejected" } };
    },
  };
}

export function createFixtureDailyClient({ accounts }) {
  return {
    async getMyDay() {
      const visible = accounts.filter((account) => canFixtureOpen(account.id));
      const profile = getFixtureRoleProfile(fixturePerson.role);
      const byId = new Map(visible.map((account) => [account.id, account]));
      const actions = profile.actions.map(([match, title, reason, next], index) => {
        const account = [...byId.values()].find((item) => item.id.includes(match));
        return account ? { kind: profile.label, accountId: account.id, name: account.name, title, reason, next, score: String(account.score), tone: index === 0 ? "hot" : "warm" } : null;
      }).filter(Boolean);
      return { status: "ready", data: {
        title: `Today for ${fixturePerson.name}`, access: "allowed", conclusion: profile.conclusion,
        workbench: { profile: { label: profile.label, eyebrow: profile.eyebrow, focus: profile.focus, riskTitle: profile.riskTitle, coverageTitle: profile.coverageTitle, signalTitle: profile.signalTitle, showRisk: profile.showRisk }, actions },
        sections: [{ heading: "Leads To Act On", bullets: [], table: { columns: ["Lead", "Score", "Score band", "Stage", "Why now", "Next action", "Linked deal"], rows: [] } },
          { heading: "Deal Risk", bullets: ["Open the account to review current risk and next action."], table: { columns: [], rows: [] } }],
        citations: [], restricted: [], confidence: "medium", freshness: "fresh", as_of: "2026-08-29", next_action: "Open the first account and confirm its next step.", missing: [], text: "",
      }};
    },
  };
}
