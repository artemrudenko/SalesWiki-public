import { adaptGraphView } from "./graphAdapter.js";

export const entityTypeLabels = {
  company: "Company",
  person: "Person",
  lead: "Lead",
  deal: "Deal",
  call: "Call",
  competitor: "Competitor",
  source: "Source",
  event: "Event",
  campaign: "Campaign",
  "pain-point": "Pain point",
  "case-study": "Case study",
  task: "Task",
  claim: "Claim",
};

function buildGraphView({ id, entityId, name, code, owner, person, role, deal, stage, competitor, call, conclusion, confidence, score, sources, extraNodes = [] }) {
  const rootId = entityId;
  const evidence = sources.map((source, index) => ({
    id: `evidence:${id}:${index + 1}`,
    title: source.short,
    status: source.status === "Verified" ? "verified" : "needs-review",
    as_of: source.date,
    summary: source.summary,
    citation: { boundary: index === 2 ? "sales-confidential" : "internal", path: source.code },
  }));
  const evidenceIds = evidence.map((item) => item.id);
  const node = (nodeId, type, label, subtitle, detail, metadata = {}, nodeEvidence = []) => ({
    id: nodeId,
    type,
    label,
    subtitle,
    detail,
    metadata,
    evidence_ids: nodeEvidence,
  });

  const nodes = [
    node(rootId, "company", name, "Target account", conclusion, { code, owner, access_label: "Internal · Sales & Marketing" }, evidenceIds),
    node(`person:${id}:primary`, "person", person, role, `${person} is the main relationship for the active opportunity.`, { meta: "Primary contact" }, [evidenceIds[1]]),
    node(`deal:${id}:active`, "deal", deal, stage, `${deal} is currently in ${stage}. The next step should be explicit and dated.`, { owner }, [evidenceIds[1]]),
    node(`competitor:${id}:primary`, "competitor", competitor, "Incumbent / alternative", `${competitor} appears in restricted competitive context. Access is checked before retrieval.`, { meta: `${sources.length} sources` }, [evidenceIds[2]]),
    node(`call:${id}:latest`, "call", call, sources[1].date, `${call} contains a sanitized summary. The raw transcript remains behind the personal-data boundary.`, { meta: "Last interaction" }, [evidenceIds[1]]),
    ...sources.map((source, index) => node(`source:${id}:${index + 1}`, "source", source.short, source.date, source.summary, { code: source.code }, [evidenceIds[index]])),
    ...extraNodes.map((item, index) => node(
      `${item.type}:${id}:${index + 1}`,
      item.type,
      item.label,
      item.subtitle,
      item.detail,
      item.metadata ?? {},
      [evidenceIds[item.evidenceIndex ?? 0]],
    )),
  ];

  return {
    contract: "saleswiki.graph-view",
    version: 1,
    root_id: rootId,
    access: "allowed",
    summary: {
      title: name,
      conclusion,
      confidence: confidence.toLowerCase(),
      freshness: "Updated today",
      as_of: "2026-08-29",
      next_action: conclusion.split(". ").slice(1).join(". ") || "Confirm the next step.",
      score,
    },
    nodes,
    edges: [
      { id: `edge:${id}:person`, type: "PERSON_WORKS_AT_COMPANY", from: `person:${id}:primary`, to: rootId, label: "KEY CONTACT", evidence_ids: [evidenceIds[1]] },
      { id: `edge:${id}:deal`, type: "DEAL_WITH_COMPANY", from: rootId, to: `deal:${id}:active`, label: "ACTIVE DEAL", evidence_ids: [evidenceIds[1]] },
      { id: `edge:${id}:competitor`, type: "COMPANY_COMPETES_WITH_COMPANY", from: rootId, to: `competitor:${id}:primary`, label: "COMPETITOR MENTIONED", evidence_ids: [evidenceIds[2]] },
      { id: `edge:${id}:call`, type: "RELATED_TO", from: rootId, to: `call:${id}:latest`, label: "LAST INTERACTION", evidence_ids: [evidenceIds[1]] },
      ...sources.map((_, index) => ({ id: `edge:${id}:source:${index + 1}`, type: "RELATED_TO", from: `source:${id}:${index + 1}`, to: rootId, label: index === 1 ? "EVIDENCE FOR" : "", evidence_ids: [evidenceIds[index]] })),
      ...extraNodes.map((item, index) => ({
        id: `edge:${id}:extra:${index + 1}`,
        type: item.edgeType ?? "RELATED_TO",
        from: `${item.type}:${id}:${index + 1}`,
        to: rootId,
        label: item.edgeLabel ?? "RELATED TO",
        evidence_ids: [evidenceIds[item.evidenceIndex ?? 0]],
      })),
    ],
    evidence,
    restricted: ["Personal-data transcript body is available only through an approved handle."],
    missing: [],
  };
}

export const graphViews = [
  buildGraphView({
    id: "bluepeak",
    entityId: "demo-company-bluepeak-energy",
    name: "BluePeak Energy",
    code: "COMP-000482",
    owner: "Ivan Petrov",
    person: "VP Operations",
    role: "Champion",
    deal: "BluePeak Pilot",
    stage: "Proposal · $240k ACV",
    competitor: "RivalCorp",
    call: "Discovery call",
    confidence: "Medium",
    score: 74,
    conclusion: "BluePeak is actively evaluating an ROI-focused pilot. Confirm the next step, engage the economic buyer, and protect the discount floor.",
    sources: [
      { short: "Cost Reduction Signal", date: "Jul 3, 2026", code: "SRC-045671", status: "Verified", summary: "Operations teams must quantify time-to-value before the next planning cycle." },
      { short: "Discovery Call", date: "Jul 3, 2026", code: "SRC-045322", status: "Verified", summary: "The champion is engaged; technical validation is positive; finance buy-in is still needed." },
      { short: "Competitor Intel", date: "Jul 3, 2026", code: "SRC-044990", status: "Needs review", summary: "RivalCorp is the incumbent, but the buying committee is frustrated by slow reporting configuration." },
    ],
    extraNodes: [
      { type: "person", label: "Finance Director", subtitle: "Economic buyer", detail: "Owns budget approval and needs a clear ROI case before the pilot can move forward.", metadata: { meta: "Budget owner" }, evidenceIndex: 1, edgeType: "PERSON_WORKS_AT_COMPANY", edgeLabel: "ECONOMIC BUYER" },
      { type: "person", label: "Solutions Architect", subtitle: "Technical evaluator", detail: "Validates implementation fit and the measurement plan with the operations team.", metadata: { meta: "Technical evaluator" }, evidenceIndex: 1, edgeType: "PERSON_WORKS_AT_COMPANY", edgeLabel: "TECHNICAL EVALUATOR" },
      { type: "call", label: "Technical validation", subtitle: "Jul 5, 2026", detail: "Follow-up confirmed the measurable pilot scope and implementation assumptions.", metadata: { meta: "Follow-up activity" }, evidenceIndex: 1, edgeLabel: "FOLLOW-UP CALL" },
      { type: "task", label: "Confirm finance workshop", subtitle: "Due Sep 4", detail: "Schedule the economic-buyer session before commercial terms are discussed.", metadata: { meta: "Next step" }, evidenceIndex: 0, edgeLabel: "NEXT STEP" },
    ],
  }),
  buildGraphView({
    id: "atlas",
    entityId: "demo-company-atlas-foods",
    name: "Atlas Foods",
    code: "COMP-000517",
    owner: "Ivan Petrov",
    person: "Quality Director",
    role: "Evaluation lead",
    deal: "Atlas Pilot",
    stage: "Discovery · $160k ACV",
    competitor: "FoodChain Systems",
    call: "Audit workflow call",
    confidence: "Medium",
    score: 79,
    conclusion: "Atlas is preparing for a quality-compliance audit. Lead with faster evidence gathering and a measurable implementation plan.",
    sources: [
      { short: "Compliance Audit", date: "Aug 21, 2026", code: "SRC-051102", status: "Verified", summary: "The team wants to reduce manual evidence gathering during each audit cycle." },
      { short: "Discovery Notes", date: "Aug 18, 2026", code: "SRC-051118", status: "Verified", summary: "Implementation speed and measurable ROI are the main evaluation criteria." },
      { short: "Vendor Comparison", date: "Aug 12, 2026", code: "SRC-050901", status: "Needs review", summary: "FoodChain Systems is included in the current evaluation set." },
    ],
  }),
  buildGraphView({
    id: "northstar",
    entityId: "demo-company-northstar-robotics",
    name: "Northstar Robotics",
    code: "COMP-000623",
    owner: "Maya Reed",
    person: "Plant Automation Lead",
    role: "Technical champion",
    deal: "Automation Pilot",
    stage: "Validation · $210k ACV",
    competitor: "MechRival",
    call: "Expansion review",
    confidence: "High",
    score: 84,
    conclusion: "Northstar is expanding factory automation and wants proof of changeover-time gains before adding more lines. Make the pilot measurable.",
    sources: [
      { short: "Expansion Program", date: "Aug 24, 2026", code: "SRC-062201", status: "Verified", summary: "Northstar started an automation expansion and set a changeover-time target." },
      { short: "Technical Review", date: "Aug 20, 2026", code: "SRC-062184", status: "Verified", summary: "The technical team asked for a short validation plan with baseline metrics." },
      { short: "Competitor Note", date: "Aug 14, 2026", code: "SRC-061991", status: "Needs review", summary: "MechRival remains in the account, but no final vendor decision is recorded." },
    ],
  }),
  buildGraphView({
    id: "summit-grid",
    entityId: "demo-company-summit-grid-logistics",
    name: "Summit Grid Logistics",
    code: "COMP-000731",
    owner: "Ivan Petrov",
    person: "Operations champion",
    role: "Expansion sponsor",
    deal: "Network expansion",
    stage: "Proposal · $390k ACV",
    competitor: "RouteFlow",
    call: "Network planning call",
    confidence: "High",
    score: 82,
    conclusion: "Summit Grid is coordinating an active network expansion. Align commercial scope, adoption proof, and the executive review around a measurable 30-day outcome.",
    sources: [
      { short: "Network Modernization", date: "Aug 28, 2026", code: "SRC-073100", status: "Verified", summary: "The account is modernizing reporting across warehouse operations." },
      { short: "Planning Call", date: "Aug 27, 2026", code: "SRC-073106", status: "Verified", summary: "The team confirmed a dated decision window and the executive-review path." },
      { short: "RouteFlow Context", date: "Aug 25, 2026", code: "SRC-073114", status: "Needs review", summary: "The incumbent remains in place while the account compares expansion options." },
    ],
    extraNodes: [
      { type: "event", label: "Operations Forum", subtitle: "Account event", detail: "A relevant customer event where the expansion story can be validated.", evidenceIndex: 0 },
      { type: "campaign", label: "ROI sequence", subtitle: "Account campaign", detail: "A short proof sequence supports the executive follow-up.", evidenceIndex: 1 },
      { type: "pain-point", label: "Network reporting", subtitle: "Primary pain", detail: "Warehouse teams still reconcile reporting manually.", evidenceIndex: 1 },
      { type: "case-study", label: "Sanitized proof", subtitle: "Reusable evidence", detail: "Comparable teams reduced reporting effort without exposing customer-sensitive details.", evidenceIndex: 0 },
    ],
  }),
];

export const accounts = graphViews.map(adaptGraphView);
