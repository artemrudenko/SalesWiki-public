// Shape the synthetic illustration by role. Real authorization stays in the
// service; filtering browser fixtures is not a security boundary.
export function fixtureCanSeeCommercial(accountId, role) {
  return ["sales-owner", "hos", "revops", "curator", "admin"].includes(role)
    || (role === "sales" && accountId === "demo-company-northstar-robotics");
}

export function shapeFixtureAccount(account, role) {
  if (fixtureCanSeeCommercial(account.id, role)) return account;
  const sources = account.sources.filter((source) => ["broad", "internal"].includes(source.boundary));
  const evidence = new Set(sources.map((source) => source.id));
  const nodes = account.nodes.filter((node) => node.id === account.id || (
    !["deal", "competitor"].includes(node.data.kind)
    && (!node.data.evidenceIds?.length || node.data.evidenceIds.some((id) => evidence.has(id)))
  )).map((node) => ({ ...node, data: { ...node.data, evidenceIds: (node.data.evidenceIds ?? []).filter((id) => evidence.has(id)) } }));
  const ids = new Set(nodes.map((node) => node.id));
  const edges = account.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target))
    .map((edge) => ({ ...edge, evidenceIds: (edge.evidenceIds ?? []).filter((id) => evidence.has(id)) }));
  return { ...account, access: "Demo · broad account context", nodes, edges, sources,
    restricted: ["This role's demo view uses broad account context only."],
  };
}
