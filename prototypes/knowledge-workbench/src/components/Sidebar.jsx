import { ClockCounterClockwise, Graph, Plus, ShieldCheck } from "@phosphor-icons/react";

export function Sidebar({ onHome, onImport, onHistory, view, setView, reviewCount, person, canReview }) {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      <button type="button" className="brand" onClick={onHome} aria-label="Go to SalesWiki home"><span>SW</span><strong>SalesWiki</strong><small>Knowledge Workbench</small></button>
      <nav>
        <button className={`nav-item ${view === "today" ? "is-active" : ""}`} onClick={() => setView("today")}><ClockCounterClockwise size={21} /><span>Today</span></button>
        <button className={`nav-item ${view === "explore" ? "is-active" : ""}`} onClick={() => setView("explore")}><Graph size={21} weight="fill" /><span>Explore</span></button>
        <button className="nav-item" data-tour-target="import" onClick={onImport}><Plus size={21} /><span>Import</span></button>
        {canReview && <button className={`nav-item ${view === "review" ? "is-active" : ""}`} data-tour-target="review" onClick={() => setView("review")}><ShieldCheck size={21} /><span>Review</span>{reviewCount > 0 && <em>{reviewCount}</em>}</button>}
      </nav>
      <div className="sidebar__bottom">
        <button className={`nav-item ${view === "history" ? "is-active" : ""}`} onClick={onHistory}><ClockCounterClockwise size={21} /><span>History</span></button>
        <div className="avatar" title={person ? `Synthetic demo: ${person.name}` : "Loading demo person"}>{person ? person.name.split(" ").map((part) => part[0]).join("").slice(0, 2) : "…"}</div>
      </div>
    </aside>
  );
}
