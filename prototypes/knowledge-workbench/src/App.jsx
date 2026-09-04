import { useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  applyNodeChanges,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  ArrowRight,
  Buildings,
  CaretDown,
  ChatCircleDots,
  Check,
  CircleNotch,
  ClockCounterClockwise,
  FileText,
  Funnel,
  Handshake,
  Info,
  LockKey,
  MagnifyingGlass,
  Compass,
  NotePencil,
  PhoneCall,
  Question,
  Sparkle,
  ShieldCheck,
  User,
  UsersThree,
  WarningOctagon,
  X,
} from "@phosphor-icons/react";
import { accounts, entityTypeLabels } from "./data";
import { adaptGraphView } from "./graphAdapter";
import { getFixtureRoleProfile, graphDemoScenarios, isFixtureAccountVisible } from "./graphClient";
import { createImportDrafts, summarizeImportDrafts } from "./importDrafts";
import { buildFixtureDashboard } from "./dashboardInsights";
import { Sidebar } from "./components/Sidebar";
import { createWorkbenchClients } from "./clientFactory";
import { GuidedTour, TourChooser } from "./components/GuidedTour";
import { buildTourSteps } from "./tourPlan";

const graphEndpoint = import.meta.env.VITE_SALESWIKI_GRAPH_ENDPOINT?.trim();
const { graphClient, dailyClient, importClient, reviewClient, updateClient, sessionClient, companySearchClient, guidedAnswerClient, dashboardClient } = createWorkbenchClients({ endpoint: graphEndpoint, accounts, adaptGraphView });

const iconByKind = {
  company: Buildings,
  person: User,
  deal: Handshake,
  call: PhoneCall,
  competitor: UsersThree,
  source: FileText,
};

const edgeColors = {
  contact: "#63a6ff",
  deal: "#58d69a",
  risk: "#f2b861",
  interaction: "#9f83ff",
  evidence: "#58d69a",
};

function EntityNode({ data, selected }) {
  const Icon = iconByKind[data.kind] ?? FileText;
  return (
    <div className={`entity-node entity-node--${data.kind} ${selected ? "is-selected" : ""}`}>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
      <span className="entity-node__icon"><Icon size={17} weight="duotone" /></span>
      <div className="entity-node__copy">
        <span className="entity-node__kind">{entityTypeLabels[data.kind]}</span>
        <strong>{data.label}</strong>
        <span>{data.subtitle}</span>
      </div>
      {data.kind !== "source" && data.meta && <span className="entity-node__meta">{data.meta}</span>}
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

function MenuSelect({ value, options, onChange, label, icon: Icon }) {
  const [open, setOpen] = useState(false);
  const selected = options.find((item) => item.value === value) ?? options[0];
  return <div className="menu-select"><button type="button" className="menu-select__trigger" aria-haspopup="listbox" aria-expanded={open} aria-label={label} onClick={() => setOpen((state) => !state)}>{Icon && <Icon size={16} />}{selected.label}<CaretDown size={14} /></button>{open && <div className="menu-select__list" role="listbox" aria-label={label}>{options.map((item) => <button type="button" role="option" aria-selected={item.value === value} className={item.value === value ? "is-selected" : ""} key={item.value} onClick={() => { onChange(item.value); setOpen(false); }}><strong>{item.label}</strong>{item.meta && <small>{item.meta}</small>}</button>)}</div>}</div>;
}

function InfoTip({ children }) {
  return <span className="info-tip"><button type="button" aria-label={`More information: ${children}`}><Info size={14} weight="fill" /></button><span role="tooltip">{children}</span></span>;
}

function History({ items }) {
  return <section className="daily-view"><div className="daily-view__heading"><div><span className="eyebrow">This browser session</span><h1>Activity history</h1><p>Shows actions performed in this Workbench session. The authoritative, auditable proposal history remains in the governed review workflow.</p></div></div><div className="daily-actions">{items.length ? items.map((item) => <article className="daily-card" key={item.id}><div><span>{item.when}</span><h2>{item.title}</h2><p>{item.detail}</p></div></article>) : <article className="daily-card"><div><span>No activity yet</span><h2>Start from an account</h2><p>Submitted updates, imports, monitoring plans and review decisions will appear here.</p></div></article>}</div></section>;
}

function DashboardInsights({ dashboard, commercial, onOpenAccount }) {
  if (!dashboard) return null;
  const profile = dashboard.profile ?? {};
  const showRisk = profile.showRisk ?? commercial;
  const coverageLabels = [["buyer", "Buyer"], ["next", "Next"], ["evidence", "Evidence"], ["monitor", "Monitor"]];
  return <section className="dashboard-insights" aria-label="Decision signals" data-tour-target="decision-signals">
    <div className="dashboard-insights__heading"><div><span className="eyebrow">{profile.focus ?? "Decision signals"}</span><h2>What changed, what is covered, what is new</h2></div><span>Synthetic demo data</span></div>
    <div className={`dashboard-insights__grid ${showRisk ? "" : "dashboard-insights__grid--signals"}`}>
      {showRisk && <article className="insight-card insight-card--risk"><header><div><span>Risk momentum</span><h3 className="insight-card__title" title={profile.riskTitle || "7-day score movement"}>{profile.riskTitle || "7-day score movement"}</h3></div><div className="insight-card__meta"><small>Evidence-backed demo baseline</small><InfoTip>Shows change between dated, permitted synthetic observations. It is not a forecast.</InfoTip></div></header><div className="risk-list">{dashboard.risk.map((item) => <button key={item.id} onClick={() => onOpenAccount(item.id)}><span className="risk-list__name"><strong>{item.name}</strong><small>{item.delta >= 0 ? `+${item.delta}` : item.delta} points · now {item.score}</small></span><span className="score-spark" aria-label={`${item.name}: ${item.history.join(", ")}`}>{item.history.map((score, index) => <i key={`${item.id}-${index}`} style={{ height: `${Math.max(18, score - 45)}%` }} />)}</span></button>)}</div></article>}
      <article className="insight-card insight-card--coverage"><header><div><span>Account coverage</span><h3 className="insight-card__title" title={profile.coverageTitle || "Decision readiness"}>{profile.coverageTitle || "Decision readiness"}</h3></div><div className="insight-card__meta"><small>Visible accounts only</small><InfoTip>Each marker shows whether the permitted account record has a buyer, next step, evidence and monitoring context.</InfoTip></div></header><div className="coverage-labels">{coverageLabels.map(([, label]) => <span key={label}>{label}</span>)}</div><div className="coverage-list">{dashboard.coverage.map((item) => <button key={item.id} onClick={() => onOpenAccount(item.id)}><strong>{item.name}</strong><span>{coverageLabels.map(([key, label]) => <i key={key} title={`${label}: ${item[key] ? "covered" : "missing"}`} className={item[key] ? "is-covered" : "is-missing"} />)}</span></button>)}</div></article>
      <article className="insight-card insight-card--timeline"><header><div><span>Signal timeline</span><h3 className="insight-card__title" title={profile.signalTitle || "Latest dated evidence"}>{profile.signalTitle || "Latest dated evidence"}</h3></div><div className="insight-card__meta"><small>Open a related account</small><InfoTip>Only source titles and dates already available to your role appear here.</InfoTip></div></header><div className="signal-list">{dashboard.signals.map((signal) => <button key={signal.id} onClick={() => onOpenAccount(signal.accountId)}><i className={signal.status === "Verified" ? "is-verified" : "is-review"} /><span><strong>{signal.title}</strong><small>{signal.account} · {signal.date}</small></span><ArrowRight size={14} /></button>)}</div></article>
    </div>
  </section>;
}

function MyDay({ result, dashboard, commercial, onOpenAccount, onRetry }) {
  if (result.status === "loading") return <section className="daily-view daily-view--state"><CircleNotch className="is-spinning" size={28} /><h1>Preparing your day</h1><p>Checking the safe, role-aware priorities.</p></section>;
  if (result.status !== "ready") return <section className="daily-view daily-view--state"><WarningOctagon size={28} /><h1>Daily priorities are unavailable</h1><p>The account explorer still works. Try loading the daily view again.</p><button onClick={onRetry}>Try again</button></section>;
  const leads = result.data.sections.find((section) => section.heading === "Leads To Act On")?.table?.rows ?? [];
  const deals = result.data.sections.find((section) => section.heading === "Deal Risk")?.table?.rows ?? [];
  const actions = result.data.workbench?.actions ?? [...leads.map((row) => ({ kind: "Lead", name: row[0], reason: row[4], next: row[5], score: row[1], tone: row[2] })), ...deals.map((row) => ({ kind: "Deal at risk", name: row[0], reason: row[4], next: row[5], score: row[1], tone: "risk" }))].slice(0, 7);
  const profile = result.data.workbench?.profile;
  return <section className="daily-view">
    <div className="daily-view__heading" data-tour-target="today-queue"><div><span className="eyebrow">{profile?.eyebrow ?? "Your daily queue"}</span><h1>{result.data.title ?? "Today for me"}{profile && <em className="daily-role">{profile.label}</em>}</h1><p>{result.data.conclusion}</p></div><span className="daily-view__freshness">Freshness: {result.data.freshness}</span></div>
    <section className="workspace-pulse" aria-label="Workspace pulse"><div><span>READY TO ACT</span><strong>{actions.length}</strong><small>role-visible priorities</small></div><div><span>FRESHNESS</span><strong>{result.data.freshness === "fresh" ? "Current" : result.data.freshness}</strong><small>last reviewed {result.data.as_of}</small></div><div><span>ACCESS</span><strong>{result.data.restricted.length ? "Scoped" : "Open"}</strong><small>{result.data.restricted.length ? "some detail stays protected" : "no hidden alerts"}</small></div></section>
    <div className="daily-actions">{actions.map((action) => <article className={`daily-card daily-card--${action.tone}`} key={`${action.kind}-${action.name}`}><div><span>{action.kind} · {action.score === "—" ? "needs review" : `score ${action.score}`}</span><h2>{action.title ?? action.name}</h2><p><strong>{action.title ? "Account:" : "Why now:"}</strong> {action.title ? action.name : action.reason}</p><p><strong>{action.title ? "Why now:" : "Next:"}</strong> {action.title ? action.reason : action.next}</p>{action.title && <p><strong>Next:</strong> {action.next}</p>}</div><button onClick={() => onOpenAccount(action.accountId ?? action.name)}>Open account <ArrowRight size={16} /></button></article>)}</div>
    <DashboardInsights dashboard={dashboard} commercial={commercial} onOpenAccount={onOpenAccount} />
    {result.data.restricted.length > 0 && <p className="daily-view__note"><ShieldCheck size={16} />Some commercial detail is hidden for this role.</p>}
  </section>;
}

const reviewCopy = {
  ingest_resource: { label: "Import draft", tone: "import", action: "Review the proposed fields and source mapping." },
  flag_stale_or_wrong: { label: "Data correction", tone: "correction", action: "Confirm whether the account record needs an update." },
  request_redaction_review: { label: "Privacy review", tone: "privacy", action: "Check the material before it is visible more broadly." },
  request_access: { label: "Access request", tone: "access", action: "Confirm that scoped access is justified." },
};

function accountForProposal(target) {
  const value = String(target ?? "").toLowerCase();
  return accounts.find((account) => value === account.id.toLowerCase() || value.includes(account.id.toLowerCase()) || value.includes(account.name.toLowerCase()));
}

function ReviewInbox({ result, onRetry, onDecision, onOpenAccount }) {
  const [selectedId, setSelectedId] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [sending, setSending] = useState(false);
  if (result.status === "loading") return <section className="review-view review-view--state"><CircleNotch className="is-spinning" size={28} /><h1>Opening the review queue</h1><p>Checking the reviewer role and pending proposals.</p></section>;
  if (result.status !== "ready") return <section className="review-view review-view--state"><WarningOctagon size={28} /><h1>Review queue is unavailable</h1><p>No proposal was changed. Try loading the queue again.</p><button onClick={onRetry}>Try again</button></section>;
  const { access, can_decide: canDecide, items } = result.data;
  if (access !== "allowed") return <section className="review-view review-view--state"><LockKey size={28} /><h1>Review access is required</h1><p>Your current role can use the workbench but cannot inspect proposal details.</p></section>;
  const selected = items.find((item) => item.proposal_id === selectedId) ?? items[0];
  const selectedAccount = accountForProposal(selected?.target);
  async function decide(action, proposal = selected, rejectionReason = "") {
    if (!proposal) return;
    setSending(true);
    const response = await onDecision({ proposalId: proposal.proposal_id, action, reason: rejectionReason });
    setSending(false);
    if (response.status === "ready") { setRejectOpen(false); setReason(""); }
  }
  return <section className="review-view">
    <header className="review-view__heading" data-tour-target="review"><div><span className="eyebrow">Governed review</span><h1>Proposal inbox</h1><p>{canDecide ? "Check the evidence, then make one explicit decision. Nothing is applied until the separate worker runs." : "You can inspect the queue, but only an approver can make a decision."}</p></div><span className="review-count">{items.length} waiting</span></header>
    <div className="review-layout">
      <div className="review-list" aria-label="Pending proposals">{items.length ? items.map((item) => { const copy = reviewCopy[item.type] ?? { label: "Proposal", tone: "correction", action: "Review the requested change." }; return <button key={item.proposal_id} className={`review-row review-row--${copy.tone} ${selected?.proposal_id === item.proposal_id ? "is-active" : ""}`} onClick={() => setSelectedId(item.proposal_id)}><span className="review-row__status">{item.status === "approved" ? "Queued" : "Needs decision"}</span><strong>{copy.label}</strong><small>{item.target} · {item.proposal_id}</small></button>; }) : <p className="review-empty">No proposals are waiting for review.</p>}</div>
      {selected && <article className="review-detail"><div className="review-detail__head"><div><span className={`review-kind review-kind--${(reviewCopy[selected.type] ?? {}).tone ?? "correction"}`}>{(reviewCopy[selected.type] ?? {}).label ?? "Proposal"}</span><h2>{selected.proposal_id}</h2></div><span className={`proposal-state proposal-state--${selected.status}`}>{selected.status === "approved" ? "Queued for apply" : "Needs decision"}</span></div><div className="review-detail__body"><section><span>Review summary</span><p>{selected.note}</p></section><dl><div><dt>Account</dt><dd>{selectedAccount ? <button className="review-account-link" onClick={() => onOpenAccount(selectedAccount.id)}>Open {selectedAccount.name} <ArrowRight size={13} /></button> : selected.target}</dd></div><div><dt>Requested by</dt><dd>{selected.requester} · {selected.role}</dd></div><div><dt>Created</dt><dd>{selected.created || "Not recorded"}</dd></div></dl><section className="review-next"><span>Recommended check</span><p>{(reviewCopy[selected.type] ?? {}).action ?? "Review the proposal against its source."}</p></section></div>{selected.status === "draft" && <div className="review-actions">{canDecide ? <><button className="review-reject" disabled={sending} onClick={() => setRejectOpen(true)}>Send back</button><button className="review-approve" disabled={sending} onClick={() => decide("approve")}>{sending ? "Saving…" : "Approve for apply"}<Check size={16} /></button></> : <p><LockKey size={15} />Decision requires an approver role.</p>}</div>}</article>}
    </div>
    {rejectOpen && <div className="modal-backdrop" role="presentation"><form className="proposal-modal review-reject-modal" role="dialog" aria-modal="true" onSubmit={(event) => { event.preventDefault(); if (reason.trim()) decide("reject", selected, reason); }}><button type="button" className="modal-close" onClick={() => setRejectOpen(false)} aria-label="Close"><X size={18} /></button><span className="eyebrow">Return for clarification</span><h2>What needs to change?</h2><p>This records a rejection in the append-only proposal history. No card is changed.</p><label>Reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} maxLength={240} placeholder="For example: link the note to the correct company." /></label><div className="modal-actions"><button type="button" onClick={() => setRejectOpen(false)}>Cancel</button><button type="submit" disabled={!reason.trim() || sending}>{sending ? "Sending…" : "Return proposal"}<ArrowRight size={16} /></button></div></form></div>}
  </section>;
}

function Topbar({ account, accountId, setAccountId, canBrowseAccounts, search, setSearch, searchRef, searchResult, onOpenSearchResult, accessLabel, accessTitle, onStarter, onHelp, onTour, session, onPersonaChange }) {
  return (
    <header className="topbar">
      {canBrowseAccounts ? <div data-tour-target="account-switcher"><MenuSelect value={accountId} label="Select company" icon={Buildings} onChange={setAccountId} options={accounts.map((item) => ({ value:item.id, label:item.name, meta:item.code }))} /></div> : <div className="current-account" aria-label="Current company" data-tour-target="account-switcher"><Buildings size={17} /><span><small>Current company</small><strong>{account.name}</strong></span></div>}
      <div className="global-search" data-tour-target="safe-search">
        <MagnifyingGlass size={18} />
        <input ref={searchRef} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find an accessible company…" aria-label="Find an accessible company" role="combobox" aria-expanded={search.trim().length >= 2} aria-controls="company-search-results" aria-autocomplete="list" />
        <kbd>⌘ K</kbd>
        {search.trim().length >= 2 && <div id="company-search-results" className="company-search-results" role="listbox" aria-label="Accessible company results">{searchResult.status === "loading" ? <span>Searching permitted companies…</span> : searchResult.status === "ready" && searchResult.items.length ? searchResult.items.map((item) => <button type="button" role="option" key={item.id} onClick={() => onOpenSearchResult(item.id)}><Buildings size={15} /><span><strong>{item.label}</strong><small>{item.freshness ? `Knowledge: ${item.freshness}` : "Accessible company"}</small></span><ArrowRight size={14} /></button>) : searchResult.status === "ready" ? <span>No accessible company matches this name.</span> : <span>Search is temporarily unavailable.</span>}</div>}
      </div>
      <div className="topbar-actions">{session?.can_switch_persona ? <div data-tour-target="persona-switcher"><MenuSelect value={session.person.id} label="Synthetic demo person" icon={User} onChange={onPersonaChange} options={session.personas.map((person) => ({ value:person.id, label:person.name, meta:person.role }))} /></div> : session?.person ? <span className="persona-static" title="Your identity is verified by the server" data-tour-target="persona-switcher"><User size={15} />{session.person.name}</span> : null}<button type="button" className="tour-trigger" onClick={onTour}><Compass size={16} weight="bold" />Tour</button><button type="button" className="help-trigger" onClick={onHelp} aria-label="Open help" title="Help"><Question size={16} weight="bold" /></button><button type="button" className="starter-trigger" onClick={onStarter}>PL starter</button><span title={accessTitle} className={`access-chip ${accessLabel.includes("blocked") ? "is-blocked" : ""}`}><ShieldCheck size={16} weight="fill" />{accessLabel ?? account.access}</span></div>
    </header>
  );
}

function DetailPanel({ account, selectedNode, onPropose, onMonitor, onBrief, monitoringPlan }) {
  const Icon = iconByKind[selectedNode.data.kind] ?? FileText;
  const relatedSources = selectedNode.data.kind === "source"
    ? account.sources.filter((source) => source.short === selectedNode.data.label)
    : account.sources;

  return (
    <aside className="detail-panel">
      <div className="detail-panel__head">
        <span className={`detail-icon detail-icon--${selectedNode.data.kind}`}><Icon size={23} weight="duotone" /></span>
        <div><span>{entityTypeLabels[selectedNode.data.kind]}</span><h2>{selectedNode.data.label}</h2></div>
        <button className="detail-panel__brief" aria-label="Open account brief" onClick={onBrief}><ChatCircleDots size={15} weight="fill" />Brief</button>
      </div>

      <section className="summary-card">
        <span className="eyebrow"><Sparkle size={15} weight="fill" />What matters now</span>
        <p>{selectedNode.data.detail}</p>
        <div className="summary-meta"><span>Confidence: {account.confidence}</span><span>Account score: {account.score}</span></div>
      </section>

      {selectedNode.id === account.id && <section className={`temperature-card temperature-card--${account.temperature}`}><span>Account temperature</span><strong>{account.temperature.replace("-", " ")}</strong><p>{account.temperatureReason}</p></section>}

      <div className="detail-section">
        <div className="section-title"><h3>Evidence</h3><span>{relatedSources.length}</span></div>
        {relatedSources.map((source) => (
          <article className="source-row" key={source.code}>
            <FileText size={18} />
            <div><strong>{source.short}</strong><span>{source.date} · {source.code}</span></div>
            <span className={source.status === "Verified" ? "status verified" : "status review"}>{source.status}</span>
          </article>
        ))}
      </div>

      <div className="detail-section facts">
        <h3>Context</h3>
        <dl>
          <div><dt>Owner</dt><dd>{account.owner}</dd></div>
          <div><dt>Freshness</dt><dd>{account.freshness}</dd></div>
          <div><dt>Access</dt><dd>Role-aware</dd></div>
        </dl>
      </div>

      <button className="proposal-button" onClick={onPropose}><NotePencil size={18} weight="bold" />Propose an update<ArrowRight size={17} /></button>
      {selectedNode.id === account.id && <><button className="monitor-button" onClick={onMonitor}><ClockCounterClockwise size={17} />Configure monitoring</button>{monitoringPlan && <p className="governed-note"><ClockCounterClockwise size={15} />Saved on this device: {monitoringPlan.topics.length} signals · {monitoringPlan.cadence}</p>}</>}
      <p className="governed-note"><ShieldCheck size={15} />Changes enter review first. The source vault is never edited directly.</p>
    </aside>
  );
}

function PolishStarter({ onClose }) {
  return <aside className="starter-panel"><div className="ask-panel__head"><div><span className="eyebrow">Polski starter</span><h2>Zacznij od jednego klienta</h2></div><button onClick={onClose} aria-label="Close"><X size={18} /></button></div><p>Nie musisz przenosić CRM. Dodaj jedną firmę, notatkę po rozmowie i następny krok.</p><ol><li><strong>Firma:</strong> nazwa, właściciel i bezpieczny link do źródła.</li><li><strong>Rozmowa:</strong> ból, obiekcja, ustalenie i data kolejnego kroku.</li><li><strong>Dzień pracy:</strong> otwórz „Today”, aby zobaczyć co zrobić i dlaczego.</li></ol><p className="governed-note"><ShieldCheck size={15} />Dane kontaktowe zostają jako bezpieczne odnośniki, zgodnie z zasadą minimalizacji danych.</p></aside>;
}

function MonitorModal({ account, initialPlan, onClose, onSave }) {
  const [topics, setTopics] = useState(initialPlan?.topics ?? ["News", "Leadership changes"]);
  const [cadence, setCadence] = useState(initialPlan?.cadence ?? "weekly");
  const options = ["News", "Leadership changes", "Hiring", "Tenders", "Competitor signals"];
  const toggle = (topic) => setTopics((items) => items.includes(topic) ? items.filter((item) => item !== topic) : [...items, topic]);
  return <div className="modal-backdrop" role="presentation"><section className="proposal-modal monitor-modal" data-tour-target="monitoring-plan" role="dialog" aria-modal="true"><button type="button" className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button><span className="eyebrow">Account monitoring <InfoTip>This saves only a local demo preference. It does not start collection, notifications or a vendor connection.</InfoTip></span><h2>What should we watch for {account.name}?</h2><p>This is a local demo configuration. It creates no background collection, notifications, or vendor connection yet.</p><div className="monitor-options" role="group" aria-label="Monitoring topics">{options.map((topic) => <label className="monitor-option" key={topic}><input type="checkbox" checked={topics.includes(topic)} onChange={() => toggle(topic)} /><span>{topic}</span></label>)}</div><label className="monitor-cadence">Review cadence<select value={cadence} onChange={(event) => setCadence(event.target.value)}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="trigger-based">Trigger-based</option></select></label><div className="modal-actions"><button onClick={onClose}>Cancel</button><button className="modal-actions__primary" type="button" onClick={() => onSave({ topics, cadence })}>Save monitoring plan<ArrowRight size={16} /></button></div></section></div>;
}

function EvidenceTrace({ sources, selectedSource, onSelect }) {
  return (
    <section className="evidence-trace" data-tour-target="evidence">
      <div className="evidence-trace__label">
        <span className="eyebrow">Evidence trace</span>
        <h3>Why this conclusion?</h3>
        <p>Every answer leads back to a dated source.</p>
      </div>
      <div className="trace-line" aria-label="Evidence sources">
        {sources.map((source, index) => (
          <button key={source.code} className={selectedSource === source.short ? "trace-item is-active" : "trace-item"} onClick={() => onSelect(source.short)}>
            <span className="trace-dot"><Check size={11} weight="bold" /></span>
            <span className="trace-index">0{index + 1}</span>
            <strong>{source.short}</strong>
            <small>{source.date}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function GraphNotice({ notice, onDismiss }) {
  const isStale = notice.kind === "stale";
  return (
    <div className={`graph-notice graph-notice--${notice.kind}`} role="status">
      {isStale ? <ClockCounterClockwise size={18} /> : <Funnel size={18} />}
      <div><strong>{notice.title}</strong><span>{notice.message}</span></div>
      <button type="button" onClick={onDismiss} aria-label={`Dismiss ${notice.title}`}><X size={15} /></button>
    </div>
  );
}

const stateCopy = {
  loading: {
    eyebrow: "Building a safe view",
    title: "Loading account knowledge",
    message: "Checking access, citations, and the graph contract before anything is shown.",
  },
  blocked: {
    eyebrow: "Access boundary",
    title: "This account is protected",
    message: "The graph was stopped before retrieval, so restricted relationships and identifiers were not sent to the browser.",
  },
  aggregated: {
    eyebrow: "Aggregate access",
    title: "Account details stay private",
    message: "Your role can use a safe aggregate, but it cannot open this company graph.",
  },
  "not-found": {
    eyebrow: "No verified match",
    title: "Company not found",
    message: "There is no matching company inside the knowledge boundary available to you.",
  },
  ambiguous: {
    eyebrow: "Identity check",
    title: "Which company did you mean?",
    message: "Several records are plausible. Choose one before SalesWiki retrieves its graph.",
  },
  "contract-error": {
    eyebrow: "Safe failure",
    title: "This graph cannot be displayed",
    message: "SalesWiki rejected a response that did not match the supported GraphView contract.",
  },
};

function StateSurface({ result, onChoose, onRetry }) {
  const copy = stateCopy[result.status] ?? stateCopy["contract-error"];
  const Icon = result.status === "loading"
    ? CircleNotch
    : result.status === "blocked"
      ? LockKey
      : result.status === "contract-error"
        ? WarningOctagon
        : MagnifyingGlass;

  return (
    <section className={`state-surface state-surface--${result.status}`} aria-live="polite" role={result.status === "contract-error" ? "alert" : "status"}>
      <span className="state-surface__icon"><Icon size={30} weight="duotone" className={result.status === "loading" ? "is-spinning" : ""} /></span>
      <span className="eyebrow">{copy.eyebrow}</span>
      <h1>{copy.title}</h1>
      <p>{result.message ?? result.reason ?? copy.message}</p>
      {result.nextAction && <p className="state-surface__next"><strong>Next step:</strong> {result.nextAction}</p>}
      {result.status === "ambiguous" && result.candidates.length > 0 && (
        <div className="candidate-list" aria-label="Possible company matches">
          {result.candidates.map((candidate) => (
            <button key={candidate.id} type="button" onClick={() => onChoose(candidate.id)}>
              <Buildings size={19} weight="duotone" />
              <span><strong>{candidate.name}</strong><small>{candidate.code}</small></span>
              <ArrowRight size={16} />
            </button>
          ))}
        </div>
      )}
      {result.status === "contract-error" && <small className="state-reference">Reference {result.reference}</small>}
      {result.status !== "loading" && (result.status !== "ambiguous" || result.candidates.length === 0) && (
        <button className="state-action" type="button" onClick={onRetry}>{result.status === "blocked" ? "Open another company" : result.status === "aggregated" ? "Open another view" : result.status === "ambiguous" ? "Use an exact identifier" : "Try again"}</button>
      )}
    </section>
  );
}

function DemoStateControl({ scenario, onChange }) {
  return (
    <label className="demo-state-control">
      <span>Demo state</span>
      <select value={scenario} onChange={(event) => onChange(event.target.value)}>
        {graphDemoScenarios.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
      </select>
    </label>
  );
}

function ImportModal({ account, onClose, onSubmit }) {
  const [source, setSource] = useState("notes");
  const [text, setText] = useState("Company: BluePeak Energy\nLead: Marta Nowak\nNext step: Confirm finance review next week");
  const [step, setStep] = useState("input");
  const [drafts, setDrafts] = useState([]);
  const [sending, setSending] = useState(false);
  const ready = drafts.filter((item) => item.state === "ready");
  function preview(event) {
    event.preventDefault();
    setDrafts(createImportDrafts({ source, text, accountName: account.name }));
    setStep("preview");
  }
  async function submit() {
    setSending(true);
    const result = await onSubmit({ target: account.id, summary: summarizeImportDrafts(drafts, account.name) });
    setSending(false);
    if (result.status === "ready") setStep("done");
  }
  return <div className="modal-backdrop" role="presentation"><section className="proposal-modal import-modal" data-tour-target="import-draft" role="dialog" aria-modal="true" aria-labelledby="import-title">
    <button type="button" className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
    {step === "input" && <form onSubmit={preview}><span className="eyebrow"><ShieldCheck size={15} weight="fill" />Controlled import</span><h2 id="import-title">Turn a note into reviewable drafts</h2><p>Paste a small CSV export or meeting note. Nothing is written to SalesWiki from this screen.</p><div className="import-source"><button type="button" className={source === "notes" ? "is-active" : ""} onClick={() => setSource("notes")}>Meeting note</button><button type="button" className={source === "csv" ? "is-active" : ""} onClick={() => setSource("csv")}>CSV rows</button></div><label>{source === "csv" ? "CSV with Company, Contact and Next step columns" : "Use Company:, Lead: and Next step: lines"}<textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={12000} /></label><p className="governed-note"><ShieldCheck size={15} />Keep full contact details and raw exports outside this demo vault.</p><div className="modal-actions"><button type="button" onClick={onClose}>Cancel</button><button type="submit">Preview drafts <ArrowRight size={16} /></button></div></form>}
    {step === "preview" && <><span className="eyebrow">Step 2 of 3 · Review</span><h2 id="import-title">Check every proposed card</h2><p>Only drafts that match the open account can enter review. Resolve unmatched companies before sending them.</p><div className="import-drafts">{drafts.length ? drafts.map((item) => <article key={item.id} className={`import-draft import-draft--${item.state}`}><span>{item.kind.replace("-", " ")}</span><strong>{item.title}</strong><small>{item.detail}</small><em>{item.state === "ready" ? "Ready" : "Needs match"}</em></article>) : <p>No usable fields found. Try the shown labels or CSV headers.</p>}</div><div className="modal-actions"><button onClick={() => setStep("input")}>Back</button><button type="button" disabled={!ready.length || sending} onClick={submit}>{sending ? "Sending…" : `Send ${ready.length} draft${ready.length === 1 ? "" : "s"} to review`} <ArrowRight size={16} /></button></div></>}
    {step === "done" && <><span className="eyebrow"><Check size={15} weight="bold" />Step 3 of 3 · Submitted</span><h2 id="import-title">Drafts are in review</h2><p>The reviewer receives the selected account and a concise draft summary. The original text stays out of the vault; no entity card has been created or changed.</p><div className="modal-actions"><button type="button" onClick={onClose}>Done</button></div></>}
  </section></div>;
}

function ProposalModal({ account, onClose, onSubmit }) {
  const [note, setNote] = useState("");
  const [source, setSource] = useState("");
  const [sending, setSending] = useState(false);
  async function submit(event) {
    event.preventDefault();
    if (!note.trim() || !source.trim()) return;
    setSending(true);
    const result = await onSubmit({ target: account.id, note: `${note.trim()} Evidence: ${source.trim()}` });
    setSending(false);
    if (result.status === "ready") onClose();
  }
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form className="proposal-modal" role="dialog" aria-modal="true" aria-labelledby="proposal-title" onMouseDown={(event) => event.stopPropagation()} onSubmit={submit}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        <span className="eyebrow"><ShieldCheck size={15} weight="fill" />Governed update</span>
        <h2 id="proposal-title">Propose a change to {account.name}</h2>
        <p>Your evidence and reasoning will be recorded with the proposal. An authorized reviewer decides what enters the vault.</p>
        <label>What changed?<textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Example: Finance agreed to join the next call on September 4." required /></label>
        <label>Source or evidence link<input value={source} onChange={(event) => setSource(event.target.value)} placeholder="https://... or raw/calls/..." required /></label>
        <div className="modal-actions"><button type="button" onClick={onClose}>Cancel</button><button type="submit" disabled={sending}>{sending ? "Sending…" : "Submit for review"}<ArrowRight size={16} /></button></div>
      </form>
    </div>
  );
}

const salesGuidedQuestions = [
  ["account_brief", "Account brief"], ["what_changed", "What changed?"], ["next_step", "What should I do next?"], ["deal_risk", "What puts this at risk?"], ["call_prep", "Prepare me for a call"],
];

const guidedQuestionsByRole = {
  marketing: [
    ["next_step", "What should marketing do next?"],
    ["what_changed", "Which signal changed?"],
    ["account_brief", "What context can we use?"],
  ],
  curator: [
    ["what_changed", "What changed?"],
    ["account_brief", "What evidence supports this?"],
    ["next_step", "What should be checked next?"],
  ],
  admin: [
    ["what_changed", "What changed?"],
    ["account_brief", "What evidence is available?"],
    ["next_step", "What should be checked next?"],
  ],
};

function HelpPanel({ onClose }) {
  return <aside className="help-panel" role="dialog" aria-modal="true" aria-label="How SalesWiki Workbench works">
    <div className="ask-panel__head"><div><span className="eyebrow">Workbench help</span><h2>Work with evidence, not guesses</h2></div><button onClick={onClose} aria-label="Close help"><X size={18} /></button></div>
    <div className="help-panel__body">
      <details className="help-topic"><summary>Start with Today</summary><p>It shows the priorities that your current role is allowed to see. Open an account to inspect the supporting evidence.</p></details>
      <details className="help-topic"><summary>Compare roles</summary><p>In this synthetic demo, changing the person also changes the Today queue, permitted accounts, decision-signal cards and Review access. It demonstrates a server-owned role boundary; it is not an account switcher for production use.</p></details>
      <details className="help-topic"><summary>Explore safely</summary><p>Search returns accessible companies only. Some graph detail can be hidden when it belongs to another team or a protected boundary.</p></details>
      <details className="help-topic"><summary>Ask assistant</summary><p>Choose a focused question for the current account. It is not free-form AI chat: each answer comes from permitted, cited SalesWiki data.</p></details>
      <details className="help-topic"><summary>Understand evidence</summary><p><strong>Verified</strong> is ready to use. <strong>Needs review</strong> is a signal that should be checked before acting. Every conclusion should lead back to a dated source.</p></details>
      <details className="help-topic"><summary>Review and monitoring</summary><p>Monitoring is a local demo plan only. Review is visible to roles that can inspect proposals; approval records a decision, and a separate governed worker applies approved changes later.</p></details>
      <p className="governed-note"><ShieldCheck size={15} />This demo uses synthetic data and server-owned demo roles. It does not connect to a customer system.</p>
    </div>
  </aside>;
}

function AskPanel({ account, role, onClose, onAsk }) {
  const guidedQuestions = guidedQuestionsByRole[role] ?? salesGuidedQuestions;
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedIntent, setSelectedIntent] = useState(guidedQuestions[0][0]);
  const [answeredIntent, setAnsweredIntent] = useState(null);
  function select(intent) {
    setSelectedIntent(intent);
    setAnsweredIntent(null);
    setResult(null);
    setError("");
  }
  async function load(intent = selectedIntent) {
    setSelectedIntent(intent);
    setLoading(true);
    const next = await onAsk({ intent, accountId: account.id });
    setLoading(false);
    if (next.status === "ready") { setResult(next.data); setAnsweredIntent(intent); setError(""); }
    else setError("This answer could not be loaded. Nothing was changed. Try again.");
  }
  return (
    <aside className="ask-panel">
      <div className="ask-panel__head"><div><span className="eyebrow">Guided assistant <InfoTip>Answers use only allowed, cited data. The assistant does not accept a free-form prompt in this demo.</InfoTip></span><h2>Ask about {account.name}</h2></div><button onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      <p>Choose a focused question. Answers are assembled from permitted, cited data; free-form AI chat is not enabled.</p>
      <div className="guided-questions" aria-label="Choose a focused question">{guidedQuestions.map(([intent, label]) => <button type="button" key={intent} className={selectedIntent === intent ? "is-active" : ""} aria-pressed={selectedIntent === intent} onClick={() => select(intent)} disabled={loading}>{label}</button>)}</div>
      {result && <div className="answer-card"><strong>{result.title}</strong><p>{result.conclusion}</p><span>{result.citations.length} cited sources · Confidence {result.confidence ?? "not recorded"}</span>{result.citations.length ? <ul>{result.citations.map((citation, index) => <li key={citation.id ?? citation.title ?? index}>{citation.title ?? citation.short ?? citation.code ?? "Cited source"}{citation.date ? ` · ${citation.date}` : ""}</li>)}</ul> : <small>No citations are available to this role.</small>}</div>}
      {error && <p className="ask-panel__error" role="status">{error}</p>}
      {answeredIntent !== selectedIntent && <button className="ask-panel__load" onClick={() => load()} disabled={loading}>{loading ? "Loading…" : "Ask selected question"}<ArrowRight size={16} /></button>}
    </aside>
  );
}

export function App() {
  const [view, setView] = useState("today");
  const [starterOpen, setStarterOpen] = useState(false);
  const [monitorOpen, setMonitorOpen] = useState(false);
  const [accountId, setAccountId] = useState(accounts[0].id);
  const [filter, setFilter] = useState("all");
  const [selectedNodeId, setSelectedNodeId] = useState(accounts[0].nodes[0].id);
  const [search, setSearch] = useState("");
  const [searchResult, setSearchResult] = useState({ status: "idle", items: [] });
  const [proposalOpen, setProposalOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [askOpen, setAskOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourChooserOpen, setTourChooserOpen] = useState(false);
  const [activeTour, setActiveTour] = useState(null);
  const [toast, setToast] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [layoutRevision, setLayoutRevision] = useState(0);
  const [renderedNodes, setRenderedNodes] = useState([]);
  const [dismissedNotices, setDismissedNotices] = useState([]);
  const searchRef = useRef(null);

  const initialParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const devControlsVisible = graphClient.source === "fixture" && (initialParams.get("dev") === "1" || initialParams.has("state"));
  const requestedScenario = initialParams.get("state") ?? "ready";
  const [scenario, setScenario] = useState(graphDemoScenarios.some((item) => item.value === requestedScenario) ? requestedScenario : "ready");
  const [graphResult, setGraphResult] = useState({ status: "loading" });
  const [dailyResult, setDailyResult] = useState({ status: "loading" });
  const [dailyReloadKey, setDailyReloadKey] = useState(0);
  const [dashboardResult, setDashboardResult] = useState({ status: graphEndpoint ? "loading" : "ready", data: null });
  const [reviewResult, setReviewResult] = useState({ status: "loading" });
  const [reviewReloadKey, setReviewReloadKey] = useState(0);
  const [sessionResult, setSessionResult] = useState({ status: "loading" });
  const [activity, setActivity] = useState([]);
  const [monitoringPlans, setMonitoringPlans] = useState(() => {
    try { return JSON.parse(window.localStorage.getItem("saleswiki-monitoring-plans") ?? "{}") ?? {}; } catch { return {}; }
  });
  const fixtureRole = sessionResult.status === "ready" ? sessionResult.data.person.role : "sales-owner";
  const canReview = sessionResult.status === "ready" && sessionResult.data.can_review;
  const fixtureProfile = getFixtureRoleProfile(fixtureRole);
  const fixtureDashboard = useMemo(() => ({ ...buildFixtureDashboard(accounts.filter((account) => isFixtureAccountVisible(account.id, fixtureRole)), monitoringPlans), profile: fixtureProfile }), [fixtureRole, fixtureProfile, monitoringPlans]);
  const dashboard = graphClient.source === "fixture" ? fixtureDashboard : dashboardResult.data;

  useEffect(() => { window.localStorage.setItem("saleswiki-monitoring-plans", JSON.stringify(monitoringPlans)); }, [monitoringPlans]);

  useEffect(() => {
    const controller = new AbortController();
    sessionClient.getSession({ signal: controller.signal }).then((next) => { if (!controller.signal.aborted) setSessionResult(next); }).catch(() => { if (!controller.signal.aborted) setSessionResult({ status: "error" }); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setGraphResult({ status: "loading" });
    graphClient.getEntityGraph({ accountId, scenario, signal: controller.signal }).then((nextResult) => {
      if (!controller.signal.aborted) setGraphResult(nextResult);
    }).catch((error) => {
      if (error?.name !== "AbortError" && !controller.signal.aborted) {
        setGraphResult({ status: "contract-error", message: "SalesWiki could not load this graph.", reference: "GRAPH-CLIENT-001" });
      }
    });
    return () => controller.abort();
  }, [accountId, scenario, reloadKey]);

  useEffect(() => {
    if (view !== "today") return undefined;
    const controller = new AbortController();
    setDailyResult({ status: "loading" });
    dailyClient.getMyDay({ signal: controller.signal }).then((next) => { if (!controller.signal.aborted) setDailyResult(next); }).catch(() => { if (!controller.signal.aborted) setDailyResult({ status: "error" }); });
    return () => controller.abort();
  }, [view, dailyReloadKey]);

  useEffect(() => {
    if (!dashboardClient || view !== "today") return undefined;
    const controller = new AbortController();
    setDashboardResult({ status: "loading", data: null });
    dashboardClient.getDashboard({ signal: controller.signal }).then((next) => { if (!controller.signal.aborted) setDashboardResult(next); }).catch(() => { if (!controller.signal.aborted) setDashboardResult({ status: "error", data: null }); });
    return () => controller.abort();
  }, [view, sessionResult.status === "ready" ? sessionResult.data.person.id : ""]);

  useEffect(() => {
    if (view !== "review" && !canReview) return undefined;
    const controller = new AbortController();
    setReviewResult({ status: "loading" });
    reviewClient.getQueue({ signal: controller.signal }).then((next) => { if (!controller.signal.aborted) setReviewResult(next); }).catch(() => { if (!controller.signal.aborted) setReviewResult({ status: "error" }); });
    return () => controller.abort();
  }, [view, canReview, reviewReloadKey]);

  useEffect(() => {
    const query = search.trim();
    if (query.length < 2) { setSearchResult({ status: "idle", items: [] }); return undefined; }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearchResult({ status: "loading", items: [] });
      try {
        const next = await companySearchClient.search({ query, signal: controller.signal });
        if (!controller.signal.aborted) setSearchResult(next);
      } catch {
        if (!controller.signal.aborted) setSearchResult({ status: "error", items: [] });
      }
    }, 160);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [search]);

  useEffect(() => {
    function handleKeydown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") {
        setProposalOpen(false);
        setImportOpen(false);
        setAskOpen(false);
        setHelpOpen(false);
        setTourChooserOpen(false);
        setActiveTour(null);
      }
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, []);

  const accountFallback = accounts.find((item) => item.id === accountId) ?? accounts[0];
  const account = graphResult.status === "ready" ? graphResult.data : null;
  const visibleNodes = useMemo(() => (account?.nodes ?? []).filter((node) => {
    const isRoot = node.id === account?.id;
    const groups = {
      people: ["person"],
      commercial: ["deal", "lead"],
      market: ["competitor", "product"],
      activity: ["call", "task", "event", "campaign", "pain-point", "case-study", "private-case"],
      evidence: ["source", "claim"],
    };
    const filterMatch = isRoot || filter === "all" || (groups[filter] ?? []).includes(node.data.kind);
    return filterMatch;
  }), [account, filter]);
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const selectedNode = account?.nodes.find((node) => node.id === selectedNodeId) ?? account?.nodes[0];
  const flowEdges = (account?.edges ?? []).filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)).map((edge) => ({
    ...edge,
    type: "smoothstep",
    animated: edge.kind === "evidence",
    markerEnd: { type: MarkerType.ArrowClosed, color: edgeColors[edge.kind], width: 16, height: 16 },
    style: { stroke: edgeColors[edge.kind], strokeWidth: 1.35 },
    labelStyle: { fill: "#c2c9d2", fontSize: 10, fontWeight: 700, letterSpacing: 0.55 },
    labelBgPadding: [7, 4],
    labelBgBorderRadius: 4,
    labelBgStyle: { fill: "#111720", fillOpacity: 1, stroke: edgeColors[edge.kind], strokeOpacity: 0.45, strokeWidth: 1 },
  }));

  function changeAccount(nextId, allowPendingRoleChange = false) {
    const next = accounts.find((item) => item.id === nextId);
    if (!next && graphClient.source !== "bff" && !allowPendingRoleChange) { setToast("This account is not available in the current demo."); window.setTimeout(() => setToast(""), 3200); return; }
    setAccountId(next?.id ?? nextId);
    setSelectedNodeId(next?.nodes[0].id ?? "");
    setFilter("all");
    setSearch("");
    setDismissedNotices([]);
  }
  function recordActivity(title, detail) {
    setActivity((items) => [{ id: `${Date.now()}-${items.length}`, when: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), title, detail }, ...items].slice(0, 20));
  }
  function openDailyAccount(name) {
    const next = accounts.find((item) => item.id === name || item.name === name);
    if (!next) { setToast("This account is not available in the current demo."); window.setTimeout(() => setToast(""), 3200); return; }
    changeAccount(next.id);
    setView("explore");
  }
  function openSearchResult(accountId) {
    changeAccount(accountId);
    setSearch("");
    setView("explore");
  }
  function openReviewAccount(nextId) {
    changeAccount(nextId);
    setView("explore");
  }
  function changeScenario(nextScenario) {
    setScenario(nextScenario);
    setDismissedNotices([]);
    const url = new URL(window.location.href);
    url.searchParams.set("state", nextScenario);
    window.history.replaceState({}, "", url);
  }
  function chooseCandidate(nextId) { changeScenario("ready"); changeAccount(nextId); }
  function resetLayout() {
    setLayoutRevision((value) => value + 1);
    setToast("Layout reset to the recommended view");
    window.setTimeout(() => setToast(""), 2600);
  }
  function handleNodeChanges(changes) {
    setRenderedNodes((nodes) => applyNodeChanges(changes, nodes));
  }
  function retryState() {
    if (graphResult.status === "blocked") {
      const currentIndex = accounts.findIndex((item) => item.id === accountId);
      changeAccount(accounts[(currentIndex + 1) % accounts.length].id);
    }
    if (scenario !== "ready") changeScenario("ready");
    else setReloadKey((value) => value + 1);
  }
  function selectSource(short) { const node = account.nodes.find((item) => item.data.kind === "source" && item.data.label === short); if (node) { setSelectedNodeId(node.id); setFilter("all"); } }
  async function submitProposal(payload) {
    const result = await updateClient.submit(payload);
    if (result.status === "ready") { recordActivity("Update sent to review", `${result.proposalId} for ${accountFallback.name}`); setReviewReloadKey((value) => value + 1); setToast(`${result.proposalId} added to the review queue`); window.setTimeout(() => setToast(""), 3200); }
    else { setToast("Could not submit the update. Nothing was changed."); window.setTimeout(() => setToast(""), 3200); }
    return result;
  }
  async function loadGuidedAnswer(payload) {
    return guidedAnswerClient.ask(payload);
  }
  async function submitImport(payload) {
    const result = await importClient.submit(payload);
    if (result.status === "ready") { recordActivity("Import sent to review", `${result.proposalId} for ${accountFallback.name}`); setReviewReloadKey((value) => value + 1); setToast(`${result.proposalId} added to the review queue`); window.setTimeout(() => setToast(""), 3600); }
    else { setToast("Could not submit the import. Nothing was changed."); window.setTimeout(() => setToast(""), 3600); }
    return result;
  }
  async function decideReview(payload) {
    const result = await reviewClient.decide(payload);
    if (result.status === "ready") { recordActivity("Review decision recorded", `${payload.proposalId}: ${result.data.status}`); setToast(`${payload.proposalId} ${result.data.status}`); window.setTimeout(() => setToast(""), 3200); setReviewReloadKey((value) => value + 1); }
    else { setToast("Could not record the decision. Nothing was changed."); window.setTimeout(() => setToast(""), 3200); }
    return result;
  }

  async function changePersona(actorId) {
    if (sessionResult.status !== "ready" || actorId === sessionResult.data.person.id) return;
    const result = await sessionClient.switchPersona(actorId);
    if (result.status !== "ready") { setToast("Could not switch the demo person. Nothing changed."); window.setTimeout(() => setToast(""), 3200); return; }
    setSessionResult(result);
    if (graphClient.source === "fixture") {
      const nextAccount = accounts.find((item) => isFixtureAccountVisible(item.id, result.data.person.role));
      if (nextAccount) changeAccount(nextAccount.id);
    }
    if (view === "review" && !result.data.can_review) setView("today");
    setDailyReloadKey((value) => value + 1);
    setReviewReloadKey((value) => value + 1);
    setReloadKey((value) => value + 1);
    setToast(`Synthetic demo: viewing as ${result.data.person.name} (${result.data.person.role})`);
    window.setTimeout(() => setToast(""), 3200);
  }

  function applyTourStep(tour) {
    const step = buildTourSteps(tour)[tour.index];
    if (!step) return;
    const persona = sessionResult.status === "ready" ? sessionResult.data.personas.find((item) => item.role === step.role) : null;
    if (persona && persona.id !== sessionResult.data.person.id) void changePersona(persona.id);
    // A fixture persona update changes the visible account list on the next
    // render. The tour already knows the next permitted account, so avoid a
    // transient false "not available" toast while that render catches up.
    if (step.accountId) changeAccount(step.accountId, true);
    setView(step.view);
    setAskOpen(step.panel === "assistant");
    setMonitorOpen(step.panel === "monitor");
    setProposalOpen(false);
    setImportOpen(step.panel === "import");
  }
  function startTour(tour) {
    setTourChooserOpen(false);
    setActiveTour({ ...tour, index: 0 });
  }
  function advanceTour(offset) {
    setActiveTour((current) => {
      if (!current) return current;
      const nextIndex = current.index + offset;
      const steps = buildTourSteps(current);
      if (nextIndex < 0) return current;
      if (nextIndex > steps.length) return current;
      return { ...current, index: nextIndex };
    });
  }

  const graphAccessLabel = graphResult.status === "blocked" ? "Access blocked" : graphResult.status === "aggregated" ? "Aggregate only" : account?.access ?? "Checking access";
  const accessLabel = graphClient.source === "bff"
    ? `Demo · ${sessionResult.status === "ready" ? sessionResult.data.person.role : "checking identity"}${graphResult.status === "blocked" ? " · blocked" : ""}`
    : graphAccessLabel;
  const accessTitle = graphClient.source === "bff"
    ? "The server resolves this demo persona and role. In a shared deployment, verified SSO identity replaces the demo selector."
    : graphAccessLabel;
  const activeNotices = (graphResult.notices ?? []).filter((notice) => !dismissedNotices.includes(notice.kind));

  useEffect(() => {
    setRenderedNodes(visibleNodes.map((node) => ({ ...node, selected: node.id === selectedNode?.id })));
  }, [graphResult, filter, layoutRevision]);

  useEffect(() => {
    setRenderedNodes((nodes) => nodes.map((node) => ({ ...node, selected: node.id === selectedNodeId })));
  }, [selectedNodeId]);

  useEffect(() => {
    if (activeTour) applyTourStep(activeTour);
  }, [activeTour]);

  return (
    <main className="workbench-shell">
      <Sidebar onHome={() => { setView("today"); setSearch(""); }} onImport={() => setImportOpen(true)} onHistory={() => setView("history")} view={view} setView={setView} reviewCount={reviewResult.status === "ready" ? reviewResult.data.items.length : 0} person={sessionResult.status === "ready" ? sessionResult.data.person : null} canReview={canReview} />
      <div className="workbench-main">
        <Topbar account={account ?? accountFallback} accountId={accountId} setAccountId={changeAccount} canBrowseAccounts={graphClient.source === "fixture"} search={search} setSearch={setSearch} searchRef={searchRef} searchResult={searchResult} onOpenSearchResult={openSearchResult} accessLabel={accessLabel} accessTitle={accessTitle} onStarter={() => setStarterOpen(true)} onHelp={() => setHelpOpen(true)} onTour={() => setTourChooserOpen(true)} session={sessionResult.status === "ready" ? sessionResult.data : null} onPersonaChange={changePersona} />
        {view === "today" ? <MyDay result={dailyResult} dashboard={dashboard} commercial={fixtureRole !== "marketing"} onOpenAccount={openDailyAccount} onRetry={() => setDailyReloadKey((value) => value + 1)} /> : view === "history" ? <History items={activity} /> : view === "review" ? <ReviewInbox result={reviewResult} onRetry={() => setReviewReloadKey((value) => value + 1)} onDecision={decideReview} onOpenAccount={openReviewAccount} /> : graphResult.status === "ready" ? <section className="workspace">
          <div className="graph-column">
            <div className="graph-heading" data-tour-target="graph">
              <div><span className="eyebrow">Entity explorer</span><h1>{account.name} <em className={`temperature-pill temperature-pill--${account.temperature}`}>{account.temperature.replace("-", " ")}</em></h1><p>One-hop relationship view · evidence stays attached</p></div>
              <div className="graph-actions" data-tour-target="graph-controls"><button className="filter-trigger" onClick={() => setFilter((current) => current === "all" ? "people" : "all")}><Funnel size={16} />{filter === "all" ? "People" : "All"}</button><button className="filter-trigger" onClick={resetLayout} aria-label="Reset graph layout" title="Return to the recommended layout"><ClockCounterClockwise size={16} />Reset layout</button><button className="ask-button" data-tour-target="assistant" onClick={() => setAskOpen(true)}><ChatCircleDots size={17} weight="fill" />Ask assistant</button></div>
            </div>
            <div className="filter-row">
              {[['all','All'],['people','People'],['commercial','Commercial'],['market','Market'],['activity','Activity'],['evidence','Evidence']].map(([value,label]) => <button key={value} onClick={() => setFilter(value)} className={filter === value ? "is-active" : ""}>{label}</button>)}
            </div>
            <div className="graph-stage">
              {activeNotices.map((notice) => <GraphNotice key={notice.kind} notice={notice} onDismiss={() => setDismissedNotices((items) => [...items, notice.kind])} />)}
              {visibleNodes.length ? <ReactFlow key={`${account.id}-${filter}-${layoutRevision}`} nodes={renderedNodes} edges={flowEdges} nodeTypes={nodeTypes} onNodesChange={handleNodeChanges} onNodeClick={(_, node) => setSelectedNodeId(node.id)} fitView fitViewOptions={{ padding: 0.12 }} minZoom={0.64} maxZoom={1.25} nodesDraggable nodesConnectable={false} elementsSelectable>
                <Background color="#343941" gap={24} size={1} />
                <Controls showInteractive={false} />
              </ReactFlow> : <div className="empty-state"><MagnifyingGlass size={28} /><strong>No matching knowledge</strong><span>Try another search or clear the current filter.</span><button onClick={() => { setSearch(""); setFilter("all"); }}>Clear filters</button></div>}
            </div>
            <EvidenceTrace sources={account.sources} selectedSource={selectedNode.data.kind === "source" ? selectedNode.data.label : ""} onSelect={selectSource} />
          </div>
          <DetailPanel account={account} selectedNode={selectedNode} onPropose={() => setProposalOpen(true)} onMonitor={() => setMonitorOpen(true)} onBrief={() => setAskOpen(true)} monitoringPlan={monitoringPlans[account.id]} />
        </section> : <div className="workspace-state-wrap"><StateSurface result={graphResult} onChoose={chooseCandidate} onRetry={retryState} /></div>}
      </div>
      {devControlsVisible && <DemoStateControl scenario={scenario} onChange={changeScenario} />}
      {proposalOpen && <ProposalModal account={account ?? accountFallback} onClose={() => setProposalOpen(false)} onSubmit={submitProposal} />}
      {importOpen && <ImportModal account={account ?? accountFallback} onClose={() => setImportOpen(false)} onSubmit={submitImport} />}
      {starterOpen && <PolishStarter onClose={() => setStarterOpen(false)} />}
      {monitorOpen && <MonitorModal account={account ?? accountFallback} initialPlan={monitoringPlans[(account ?? accountFallback).id]} onClose={() => setMonitorOpen(false)} onSave={({ topics, cadence }) => { const selectedAccount = account ?? accountFallback; setMonitoringPlans((plans) => ({ ...plans, [selectedAccount.id]: { topics, cadence } })); setMonitorOpen(false); recordActivity("Monitoring plan saved", `${selectedAccount.name}: ${topics.length} signals, ${cadence}`); setToast(`Monitoring plan saved: ${topics.length} signal types, ${cadence}`); window.setTimeout(() => setToast(""), 3200); }} />}
      {askOpen && account && <AskPanel account={account} role={fixtureRole} onClose={() => setAskOpen(false)} onAsk={loadGuidedAnswer} />}
      {helpOpen && <HelpPanel onClose={() => setHelpOpen(false)} />}
      {tourChooserOpen && <TourChooser personas={sessionResult.status === "ready" ? sessionResult.data.personas : []} currentRole={fixtureRole} onClose={() => setTourChooserOpen(false)} onStart={startTour} />}
      {activeTour && <GuidedTour tour={activeTour} onNext={() => advanceTour(1)} onPrevious={() => advanceTour(-1)} onClose={() => setActiveTour(null)} />}
      {toast && <div className="toast"><Check size={18} weight="bold" />{toast}</div>}
    </main>
  );
}
