const scoreHistory = {
  "demo-company-bluepeak-energy": [61, 65, 69, 74],
  "demo-company-atlas-foods": [83, 82, 80, 79],
  "demo-company-northstar-robotics": [72, 77, 81, 84],
  "demo-company-summit-grid-logistics": [75, 78, 80, 82],
};

function sourceDate(value) {
  const timestamp = Date.parse(`${value}, 2026`);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

/** Build synthetic-only dashboard data from the same account records as the graph.
 * The caller supplies accounts already permitted for the displayed demo role. */
export function buildFixtureDashboard(accounts, monitoringPlans = {}) {
  const visible = Array.isArray(accounts) ? accounts : [];
  const risk = visible.map((account) => {
    const history = scoreHistory[account.id] ?? [account.score - 4, account.score - 2, account.score - 1, account.score];
    return { id: account.id, name: account.name, history, delta: history.at(-1) - history[0], score: account.score };
  }).sort((a, b) => a.delta - b.delta || b.score - a.score).slice(0, 4);
  const coverage = visible.map((account) => {
    const people = account.nodes.filter((node) => node.data.kind === "person");
    return {
      id: account.id,
      name: account.name,
      buyer: people.some((node) => /economic buyer/i.test(node.data.subtitle)),
      next: account.nodes.some((node) => node.data.kind === "task"),
      evidence: account.sources.filter((source) => source.status === "Verified").length >= 2,
      monitor: Boolean(monitoringPlans[account.id]),
    };
  });
  const signals = visible.flatMap((account) => account.sources.map((source) => ({
    id: `${account.id}-${source.code}`,
    accountId: account.id,
    account: account.name,
    title: source.short,
    date: source.date,
    timestamp: sourceDate(source.date),
    status: source.status,
  }))).sort((a, b) => b.timestamp - a.timestamp).slice(0, 5);
  return { risk, coverage, signals };
}
