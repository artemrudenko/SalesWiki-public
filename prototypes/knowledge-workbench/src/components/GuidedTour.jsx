import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Compass, CursorClick, X } from "@phosphor-icons/react";
import { buildTourSteps, roleLabel } from "../tourPlan";

export function TourChooser({ personas, currentRole, onClose, onStart }) {
  const [role, setRole] = useState(currentRole);
  return <div className="modal-backdrop tour-chooser-backdrop" role="presentation">
    <section className="proposal-modal tour-chooser" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      <button type="button" className="modal-close" onClick={onClose} aria-label="Close tour chooser"><X size={18} /></button>
      <span className="eyebrow"><Compass size={15} weight="fill" />Guided product tour</span>
      <h2 id="tour-title">Choose how to explore SalesWiki</h2>
      <p>Each step opens a real part of the synthetic demo. The tour never creates a proposal, changes a card or connects to customer data.</p>
      <div className="tour-options">
        <button type="button" onClick={() => onStart({ mode: "full", role })}><strong>Full product tour</strong><span>See role boundaries, evidence, the assistant and the review loop.</span><ArrowRight size={16} /></button>
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
    function updateSpotlight() {
      const target = document.querySelector(`[data-tour-target="${step.target}"]`);
      if (!target) { setRect(null); return; }
      const next = target.getBoundingClientRect();
      setRect({ top: Math.max(8, next.top - 7), left: Math.max(8, next.left - 7), width: next.width + 14, height: next.height + 14 });
      target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    }
    const timer = window.setTimeout(updateSpotlight, 80);
    window.addEventListener("resize", updateSpotlight);
    return () => { window.clearTimeout(timer); window.removeEventListener("resize", updateSpotlight); };
  }, [step]);
  return <div className="tour-layer" role="dialog" aria-modal="true" aria-label={`Tour step ${tour.index + 1}: ${step.title}`}>
    {rect && <div className="tour-spotlight" style={rect}><CursorClick size={18} weight="fill" /></div>}
    <section className="tour-card">
      <div className="tour-card__head"><span>Guided tour · {tour.mode === "full" ? "Full product" : roleLabel(tour.role)}</span><button type="button" onClick={onClose} aria-label="Close guided tour"><X size={18} /></button></div>
      <div className="tour-card__progress"><i style={{ width: `${((tour.index + 1) / steps.length) * 100}%` }} /></div>
      <small>Step {tour.index + 1} of {steps.length}</small>
      <h2>{step.title}</h2>
      <p>{step.body}</p>
      <p className="tour-card__why"><strong>Why it matters</strong>{step.why}</p>
      <footer><button type="button" onClick={onClose}>Skip tour</button><div>{tour.index > 0 && <button type="button" onClick={onPrevious}><ArrowLeft size={15} />Back</button>}<button type="button" className="tour-next" onClick={onNext}>{tour.index === steps.length - 1 ? "Finish" : "Next"}<ArrowRight size={15} /></button></div></footer>
    </section>
  </div>;
}
