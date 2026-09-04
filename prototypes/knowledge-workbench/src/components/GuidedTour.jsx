import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, ArrowSquareOut, Compass, CursorClick, GithubLogo, X } from "@phosphor-icons/react";
import { buildTourSteps, roleLabel } from "../tourPlan";

export function TourChooser({ personas, currentRole, onClose, onStart }) {
  const [role, setRole] = useState(currentRole);
  return <div className="modal-backdrop tour-chooser-backdrop" role="presentation">
    <section className="proposal-modal tour-chooser" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      <button type="button" className="modal-close" onClick={onClose} aria-label="Close tour chooser"><X size={18} /></button>
      <span className="eyebrow"><Compass size={15} weight="fill" />Guided product tour</span>
      <h2 id="tour-title">How does scattered context become a trusted decision?</h2>
      <p>Follow linked cards and stable evidence through different role views, then see how that shared knowledge supports an action. The tour never creates a proposal, changes a card or connects to customer data.</p>
      <div className="tour-options">
        <button type="button" className="tour-option--recommended" onClick={() => onStart({ mode: "quick", role })}><strong>Quick product tour <em>Recommended · about 90 sec</em></strong><span>See how sales and marketing use shared evidence to reach different, inspectable next steps.</span><ArrowRight size={16} /></button>
        <button type="button" onClick={() => onStart({ mode: "full", role })}><strong>Full technical tour <em>12 steps · about 3 min</em></strong><span>Also inspect safe search, graph controls, monitoring and controlled import.</span><ArrowRight size={16} /></button>
        <div className="tour-role-option"><label htmlFor="tour-role">Tour for one role</label><select id="tour-role" value={role} onChange={(event) => setRole(event.target.value)}>{personas.map((person) => <option key={person.role} value={person.role}>{roleLabel(person.role)} · {person.name}</option>)}</select><button type="button" onClick={() => onStart({ mode: "role", role })}><strong>Explore this role</strong><ArrowRight size={16} /></button></div>
      </div>
    </section>
  </div>;
}

export function GuidedTour({ tour, onNext, onPrevious, onClose }) {
  const steps = buildTourSteps(tour);
  const step = steps[tour.index];
  const [rect, setRect] = useState(null);
  useEffect(() => {
    if (!step) { setRect(null); return undefined; }
    const targetName = window.matchMedia("(max-width: 760px)").matches && step.mobileTarget ? step.mobileTarget : step.target;
    const target = document.querySelector(`[data-tour-target="${targetName}"]`);
    function measureSpotlight() {
      if (!target) { setRect(null); return; }
      const next = target.getBoundingClientRect();
      const width = Math.min(next.width + 14, window.innerWidth - 16);
      const height = Math.min(next.height + 14, window.innerHeight - 16);
      setRect({
        top: Math.max(8, Math.min(next.top - 7, window.innerHeight - height - 8)),
        left: Math.max(8, Math.min(next.left - 7, window.innerWidth - width - 8)),
        width,
        height,
      });
    }
    function updateSpotlight() {
      if (!target) { setRect(null); return; }
      target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      measureSpotlight();
    }
    const timer = window.setTimeout(updateSpotlight, 80);
    window.addEventListener("resize", measureSpotlight);
    document.addEventListener("scroll", measureSpotlight, true);
    return () => { window.clearTimeout(timer); window.removeEventListener("resize", measureSpotlight); document.removeEventListener("scroll", measureSpotlight, true); };
  }, [step]);
  if (!step) return <div className="tour-layer" role="dialog" aria-modal="true" aria-label="Guided tour complete">
    <section className="tour-card tour-card--complete">
      <div className="tour-card__head"><span>Guided tour · Complete</span><button type="button" onClick={onClose} aria-label="Close guided tour"><X size={18} /></button></div>
      <div className="tour-card__complete-mark"><Compass size={22} weight="fill" /></div>
      <h2>From scattered context to a decision you can inspect</h2>
      <p>SalesWiki keeps one linked knowledge model, preserves its evidence and turns it into a permitted, role-specific path toward a solution.</p>
      <ul><li>Cards make the shared context navigable instead of duplicating it across team notes.</li><li>Proposals and review preserve how the shared conclusion changes.</li><li>The system suggests a defensible direction; the person still makes the decision.</li></ul>
      <div className="tour-card__complete-actions"><button type="button" onClick={onClose}>Explore on your own</button><a href="https://github.com/artemrudenko/SalesWiki-public" target="_blank" rel="noreferrer"><GithubLogo size={16} weight="fill" />View GitHub<ArrowSquareOut size={14} /></a></div>
    </section>
  </div>;
  const tourName = tour.mode === "quick" ? "Quick product" : tour.mode === "full" ? "Full technical" : roleLabel(tour.role);
  return <div className="tour-layer" role="dialog" aria-modal="true" aria-label={`Tour step ${tour.index + 1}: ${step.title}`}>
    {rect && <div className="tour-spotlight" style={rect}><CursorClick size={18} weight="fill" /></div>}
    <section className={`tour-card ${step.id === "evidence" ? "tour-card--top" : ""}`}>
      <div className="tour-card__head"><span>Guided tour · {tourName}</span><button type="button" onClick={onClose} aria-label="Close guided tour"><X size={18} /></button></div>
      <div className="tour-card__progress"><i style={{ width: `${((tour.index + 1) / steps.length) * 100}%` }} /></div>
      <small>Step {tour.index + 1} of {steps.length}</small>
      <h2>{step.title}</h2>
      <p>{step.body}</p>
      <p className="tour-card__why"><strong>Why it matters</strong>{step.why}</p>
      <footer><button type="button" onClick={onClose}>Skip tour</button><div>{tour.index > 0 && <button type="button" onClick={onPrevious}><ArrowLeft size={15} />Back</button>}<button type="button" className="tour-next" onClick={onNext}>{tour.index === steps.length - 1 ? "Finish" : "Next"}<ArrowRight size={15} /></button></div></footer>
    </section>
  </div>;
}
