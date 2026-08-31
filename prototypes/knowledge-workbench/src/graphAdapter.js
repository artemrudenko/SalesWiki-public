const ROOT_POSITION = { x: 460, y: 240 };

const sectorConfig = {
  people: { types: ["person"], anchor: { x: 460, y: 20 }, columns: 3, gapX: 330, gapY: 130 },
  commercial: { types: ["deal", "lead"], anchor: { x: 20, y: 240 }, columns: 1, gapX: 0, gapY: 150 },
  market: { types: ["competitor", "product"], anchor: { x: 900, y: 240 }, columns: 1, gapX: 0, gapY: 150 },
  activity: { types: ["call", "task", "event", "campaign", "pain-point", "case-study", "private-case"], anchor: { x: 460, y: 480 }, columns: 3, gapX: 285, gapY: 130 },
  evidence: { types: ["source", "claim"], anchor: { x: 460, y: 740 }, columns: 3, gapX: 250, gapY: 115 },
};

const typeToSector = new Map(
  Object.entries(sectorConfig).flatMap(([sector, config]) => config.types.map((type) => [type, sector])),
);

const edgePresentation = {
  PERSON_WORKS_AT_COMPANY: { kind: "contact", label: "KEY CONTACT" },
  LEAD_BELONGS_TO_COMPANY: { kind: "deal", label: "QUALIFIED LEAD" },
  DEAL_WITH_COMPANY: { kind: "deal", label: "ACTIVE DEAL" },
  COMPANY_COMPETES_WITH_COMPANY: { kind: "risk", label: "COMPETITOR MENTIONED" },
  CALL_RELATED_TO_DEAL: { kind: "interaction", label: "LAST INTERACTION" },
  SOURCE_SUPPORTS_CLAIM: { kind: "evidence", label: "EVIDENCE FOR" },
  CLAIM_SUPPORTED_BY_SOURCE: { kind: "evidence", label: "SUPPORTED BY" },
  RELATED_TO: { kind: "interaction", label: "RELATED TO" },
};

function requireContract(view) {
  if (view?.contract !== "saleswiki.graph-view" || view?.version !== 1) {
    throw new Error("Unsupported SalesWiki GraphView contract");
  }
  const emptyAccess = ["aggregated", "blocked", "not-found", "ambiguous"].includes(view.access);
  if (emptyAccess) {
    if (view.root_id !== null || view.nodes.length || view.edges.length || view.evidence.length) {
      throw new Error("Empty GraphView state contains a root or hidden records");
    }
    return;
  }
  const nodeIds = new Set(view.nodes.map((node) => node.id));
  if (nodeIds.size !== view.nodes.length || !nodeIds.has(view.root_id)) {
    throw new Error("GraphView has a missing root or duplicate node IDs");
  }
  for (const edge of view.edges) {
    if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) {
      throw new Error(`GraphView edge ${edge.id} has a hidden or missing endpoint`);
    }
  }
  const evidenceIds = new Set(view.evidence.map((item) => item.id));
  for (const item of [...view.nodes, ...view.edges]) {
    if (item.evidence_ids.some((id) => !evidenceIds.has(id))) {
      throw new Error(`GraphView item ${item.id} references missing evidence`);
    }
  }
}

function positionsFor(nodes, rootId) {
  const positions = new Map([[rootId, ROOT_POSITION]]);
  const grouped = new Map();

  for (const node of nodes) {
    if (node.id === rootId) continue;
    const sector = typeToSector.get(node.type) ?? "activity";
    grouped.set(sector, [...(grouped.get(sector) ?? []), node]);
  }

  for (const [sector, unsortedItems] of grouped) {
    const config = sectorConfig[sector];
    const typeOrder = new Map(config.types.map((type, index) => [type, index]));
    const items = [...unsortedItems].sort((left, right) => (
      (typeOrder.get(left.type) ?? 999) - (typeOrder.get(right.type) ?? 999)
      || left.label.localeCompare(right.label)
    ));
    items.forEach((node, index) => {
      const row = Math.floor(index / config.columns);
      const column = index % config.columns;
      const columnsInRow = Math.min(config.columns, items.length - row * config.columns);
      const position = {
        x: config.anchor.x - ((columnsInRow - 1) * config.gapX) / 2 + column * config.gapX,
        y: config.anchor.y + row * config.gapY,
      };
      positions.set(node.id, position);
    });
  }
  return positions;
}

function metaFor(node) {
  if (node.metadata.meta) return String(node.metadata.meta);
  if (node.metadata.owner) return `Owner: ${node.metadata.owner}`;
  const technical = new Set(["code", "boundary", "freshness", "updated", "access_label"]);
  const first = Object.entries(node.metadata).find(([key]) => !technical.has(key));
  return first ? `${first[0].replaceAll("_", " ")}: ${first[1]}` : "";
}

function edgeStyle(edge, nodesById) {
  if (edge.type === "RELATED_TO" && nodesById.get(edge.from)?.type === "source") {
    return { kind: "evidence", label: edge.label || "EVIDENCE FOR" };
  }
  const base = edgePresentation[edge.type] ?? { kind: "contact", label: edge.type.replaceAll("_", " ") };
  return { kind: base.kind, label: edge.label || base.label };
}

export function adaptGraphView(view) {
  requireContract(view);
  if (["aggregated", "blocked", "not-found", "ambiguous"].includes(view.access)) {
    throw new Error(`GraphView state ${view.access} is not renderable as an account graph`);
  }
  const positions = positionsFor(view.nodes, view.root_id);
  const nodesById = new Map(view.nodes.map((node) => [node.id, node]));
  const root = nodesById.get(view.root_id);
  const sources = view.evidence.map((item) => ({
    id: item.id,
    short: item.title,
    date: item.as_of,
    code: item.citation.path || item.citation.handle,
    status: item.status === "verified" ? "Verified" : item.status === "needs-review" ? "Needs review" : "Restricted",
    summary: item.summary,
  }));

  return {
    id: root.id,
    name: root.label,
    code: String(root.metadata.code ?? root.id),
    owner: String(root.metadata.owner ?? "Unassigned"),
    access: String(root.metadata.access_label ?? view.access),
    freshness: `${view.summary.freshness}${view.summary.as_of ? ` · ${view.summary.as_of}` : ""}`,
    confidence: view.summary.confidence.charAt(0).toUpperCase() + view.summary.confidence.slice(1),
    score: view.summary.score ?? 0,
    temperature: String(root.metadata.temperature ?? ((view.summary.score ?? 0) >= 85 ? "hot" : (view.summary.score ?? 0) >= 70 ? "warm" : "cold")),
    temperatureReason: String(root.metadata.temperature_reason ?? "Based on the visible score and account context."),
    conclusion: view.summary.conclusion,
    nextAction: view.summary.next_action,
    restricted: view.restricted,
    missing: view.missing,
    nodes: view.nodes.map((node) => ({
      id: node.id,
      type: "entity",
      position: positions.get(node.id),
      data: {
        kind: node.type,
        label: node.label,
        subtitle: node.subtitle,
        meta: metaFor(node),
        detail: node.id === view.root_id ? view.summary.conclusion : node.detail,
        evidenceIds: node.evidence_ids,
      },
    })),
    edges: view.edges.map((edge) => ({
      id: edge.id,
      source: edge.from,
      target: edge.to,
      ...edgeStyle(edge, nodesById),
      evidenceIds: edge.evidence_ids,
    })),
    sources,
  };
}
