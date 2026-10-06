const MAX_INPUT_LENGTH = 12_000;

function clean(value) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim();
}

function csvRows(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { field += '"'; index += 1; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) { row.push(clean(field)); field = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(clean(field)); field = "";
      if (row.some(Boolean)) rows.push(row);
      row = [];
    } else field += char;
  }
  row.push(clean(field));
  if (row.some(Boolean)) rows.push(row);
  return rows;
}

function findValue(row, headers, names) {
  const index = headers.findIndex((header) => names.includes(header));
  return index >= 0 ? row[index] : "";
}

function draft(kind, title, detail, state = "ready") {
  return { id: `${kind}-${title}-${detail}`.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 96), kind, title, detail, state };
}

function fromCsv(text) {
  const rows = csvRows(text);
  if (rows.length < 2) return [];
  const headers = rows[0].map((header) => header.toLowerCase());
  const result = [];
  rows.slice(1, 6).forEach((row) => {
    const company = findValue(row, headers, ["company", "company name", "account"]);
    const lead = findValue(row, headers, ["lead", "contact", "contact name", "name"]);
    const next = findValue(row, headers, ["next step", "next action", "action"]);
    if (company) result.push(draft("company", company, "Company from CSV"));
    if (lead) result.push(draft("lead", lead, company ? `Linked to ${company}` : "Company is missing", company ? "ready" : "needs-match"));
    if (next) result.push(draft("next-step", next, company ? `For ${company}` : "Choose an account before review", company ? "ready" : "needs-match"));
  });
  return result;
}

function fromNotes(text) {
  const lines = text.split(/\r?\n/).map(clean).filter(Boolean);
  const result = [];
  for (const line of lines.slice(0, 12)) {
    const match = line.match(/^(company|firma|account|contact|lead|next step|następny krok|action)\s*:\s*(.+)$/i);
    if (!match) continue;
    const key = match[1].toLowerCase();
    const value = clean(match[2]);
    const kind = /company|firma|account/.test(key) ? "company" : /contact|lead/.test(key) ? "lead" : "next-step";
    result.push(draft(kind, value, kind === "company" ? "Company from meeting note" : "Extracted from meeting note"));
  }
  return result;
}

export function createImportDrafts({ source, text, accountName }) {
  const safeText = String(text ?? "").slice(0, MAX_INPUT_LENGTH);
  const drafts = source === "csv" ? fromCsv(safeText) : fromNotes(safeText);
  const normalizedAccount = clean(accountName).toLowerCase();
  return drafts.map((item) => item.kind === "company" && normalizedAccount && item.title.toLowerCase() !== normalizedAccount
    ? { ...item, state: "needs-match", detail: `Does not match the open account: ${accountName}` }
    : item);
}

export function summarizeImportDrafts(drafts, accountName) {
  const kept = drafts.filter((item) => item.state === "ready").slice(0, 8);
  const labels = kept.map((item) => `${item.kind}: ${item.title}`);
  return clean(`Workbench draft import for ${accountName}. ${labels.join("; ")}`).slice(0, 480);
}
