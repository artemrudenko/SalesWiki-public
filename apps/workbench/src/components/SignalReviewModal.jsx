import { useEffect, useRef, useState } from "react";
import { X } from "@phosphor-icons/react";
import { findReviewSourceNode, reviewOptions, validReviewRequest } from "../signalReviewClient.js";

const tomorrow = () => new Date(Date.now() + 86400000).toISOString().slice(0, 10);
const formatTime = (value) => value?.replace("T", " ").slice(0, 16) ?? "Not recorded";

export function SignalReviewModal({ account, person, client, touring = false, onClose, onSaved, onInspect, onPropose }) {
  const [result, setResult] = useState({ status: "loading" });
  const [reload, setReload] = useState(0);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");
  const [anotherCheck, setAnotherCheck] = useState(false);
  const [form, setForm] = useState({ outcome: "", cause: "unknown", cause_status: "unknown", decision_impact: "cannot_assess", next_action: "verify_source", follow_up_on: tomorrow(), evidence_ids: [] });
  const dialog = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    setResult({ status: "loading" });
    client.get({ target: account.id, signal: controller.signal }).then((next) => {
      if (!controller.signal.aborted) setResult(next);
    }).catch(() => { if (!controller.signal.aborted) setResult({ status: "error" }); });
    return () => controller.abort();
  }, [account.id, client, reload, person.id]);

  useEffect(() => {
    if (touring) return undefined;
    const priorFocus = document.activeElement;
    dialog.current?.querySelector("h2")?.focus();
    function trap(event) {
      if (event.key !== "Tab") return;
      const elements = [...dialog.current.querySelectorAll("button:not(:disabled), select, input:not(:disabled), summary")].filter((element) => element.getClientRects().length);
      const first = elements[0], last = elements.at(-1);
      if (event.shiftKey && (!elements.includes(document.activeElement) || document.activeElement === first)) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (!elements.includes(document.activeElement) || document.activeElement === last)) { event.preventDefault(); first?.focus(); }
    }
    const element = dialog.current;
    element.addEventListener("keydown", trap);
    return () => { element.removeEventListener("keydown", trap); priorFocus?.focus?.(); };
  }, [touring]);

  const data = result.data;
  const active = data?.can_complete;
  const latest = data?.events.at(-1);
  const field = (key, values = reviewOptions[key]) => <label>{({ outcome: "What did you find?", decision_impact: "Effect on the next decision", next_action: "Next step", cause_status: "How certain is the cause?", cause: "Possible reason for the delay" })[key]}<select value={form[key]} onChange={(event) => {
    const value = event.target.value;
    setForm((previous) => ({ ...previous, [key]: value,
      ...(key === "cause_status" && value === "unknown" ? { cause: "unknown" } : {}),
      ...(key === "cause_status" && value !== "unknown" && previous.cause === "unknown" ? { cause: "source_changed" } : {}),
      ...(key === "next_action" ? { follow_up_on: value === "none" ? "" : previous.follow_up_on || tomorrow() } : {}),
    }));
  }}>{key === "outcome" && <option value="">Choose a result</option>}{Object.entries(values).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>;

  async function save(event) {
    event.preventDefault();
    const request = { target: account.id, action: active ? "complete" : "start", expected_revision: data.revision,
      ...form, ...(!active ? { outcome: "", cause: "unknown", cause_status: "unknown", decision_impact: "not_assessed", evidence_ids: [] } : {}) };
    if (!validReviewRequest(request) || (request.follow_up_on && request.follow_up_on < new Date().toISOString().slice(0, 10))) {
      setMessage("Choose a result and next step. Link a source for a confirmed result or possible cause, and use a current follow-up date.");
      return;
    }
    setSending(true);
    let saved;
    try { saved = await client.record(request); } catch { saved = { status: "error" }; }
    setSending(false);
    if (saved.status === "ready") {
      setAnotherCheck(false);
      setMessage(active ? "Check result recorded. Card freshness and priority still follow the stored evidence." : "You took this check. Compare the sources before recording a result.");
      onSaved(active ? "Check result recorded" : "Context check started");
      setForm({ outcome: "", cause: "unknown", cause_status: "unknown", decision_impact: "cannot_assess", next_action: "verify_source", follow_up_on: tomorrow(), evidence_ids: [] });
      setReload((value) => value + 1);
    } else {
      setMessage(saved.status === "conflict" ? "This check changed in another tab. Reload it before continuing." : "Saving was not confirmed. Reload the history before trying again.");
      setResult({ status: "error" });
    }
  }

  return <div className="modal-backdrop"><section className="proposal-modal signal-review-modal" ref={dialog} data-tour-target="signal-review" role="dialog" aria-modal={!touring} aria-labelledby="signal-review-title">
    <button type="button" className="modal-close" onClick={onClose} aria-label="Close context check"><X size={18} /></button>
    <span className="eyebrow">Your context check · {client.mode === "fixture" ? "synthetic session" : "demo journal"}</span>
    <h2 id="signal-review-title" tabIndex={-1}>What needs checking for {account.name}?</h2>
    <p>Check the evidence behind your next decision. Old information can still matter; age alone does not explain a missed review.</p>
    <p className="signal-review-scope">{client.mode === "fixture" ? "Checks stay in this tab and reset on reload." : "Your checks are recorded in the demo runtime journal."} Each role sees its own checks. A result here does not update the account card.</p>
    {message && <p className="signal-review-message" role="status">{message}</p>}
    {result.status === "loading" ? <p role="status">Opening your check history…</p> : result.status !== "ready" ? <div><p>Could not open this check. No result is shown as saved.</p><button className="signal-review-primary" onClick={() => setReload((value) => value + 1)}>Reload history</button></div> : <>
      <dl className="signal-review-summary"><div><dt>Your check</dt><dd>{data.state === "in_progress" ? "In progress" : data.state === "completed" ? "Result recorded" : "Not started"}</dd></div><div><dt>Reviewer</dt><dd>{latest ? person.name : "Not assigned"}</dd></div><div><dt>Last account review</dt><dd>{account.reviewLifecycle?.lastReviewedOn ?? "See the dated account evidence"}</dd></div><div><dt>Newest source record</dt><dd>{[...data.sources].filter((source) => Number.isFinite(Date.parse(source.date))).sort((a, b) => Date.parse(b.date) - Date.parse(a.date))[0]?.date || "Not recorded"}</dd></div></dl>
      {latest?.outcome && <p><strong>Last result:</strong> {reviewOptions.outcome[latest.outcome]}. {reviewOptions.decision_impact[latest.decision_impact]}.</p>}
      {data.state === "completed" && <p><strong>Your recorded next step:</strong> {reviewOptions.next_action[latest.next_action]}{latest.follow_up_on ? ` · ${latest.follow_up_on}` : ""}</p>}
      <details className="signal-review-evidence" open={data.state !== "completed"}><summary>Sources to compare</summary>{data.sources.length ? data.sources.map((source) => <div key={source.id}><span>{source.label}<small>{source.date || "Date not recorded"}</small></span>{findReviewSourceNode(account, source) ? <button type="button" onClick={() => onInspect(findReviewSourceNode(account, source).id)}>Inspect source</button> : <small>Outside this focused graph. Check it in your source client.</small>}</div>) : <p>No accessible source is recorded. Request context before drawing a conclusion.</p>}</details>
      {data.state === "completed" && !anotherCheck && <button type="button" className="signal-review-primary" onClick={() => setAnotherCheck(true)}>Start another check</button>}
      <form onSubmit={save} hidden={data.state === "completed" && !anotherCheck}>
        {data.state === "completed" && <p><strong>New check:</strong> choose its next step and date.</p>}
        {active && <>
          {field("outcome")}
          {field("decision_impact", Object.fromEntries(Object.entries(reviewOptions.decision_impact).filter(([key]) => key !== "not_assessed")))}
          <fieldset><legend>Sources you checked</legend>{data.sources.map((source) => <label className="signal-review-source" key={source.id}><input type="checkbox" checked={form.evidence_ids.includes(source.id)} onChange={(event) => setForm((previous) => ({ ...previous, evidence_ids: event.target.checked ? [...previous.evidence_ids, source.id] : previous.evidence_ids.filter((id) => id !== source.id) }))} />{source.label}</label>)}</fieldset>
          <details className="signal-review-cause"><summary>Do we know why this review fell behind?</summary><p>Leave the cause unknown unless a source or recorded timeline supports it. Selecting “confirmed” records your assessment; the assistant has not verified it.</p>{field("cause_status")}{form.cause_status !== "unknown" && field("cause", Object.fromEntries(Object.entries(reviewOptions.cause).filter(([key]) => key !== "unknown")))}</details>
        </>}
        {field("next_action", active ? reviewOptions.next_action : Object.fromEntries(Object.entries(reviewOptions.next_action).filter(([key]) => key !== "none")))}
        {form.next_action !== "none" && <label>Next check date<input type="date" min={new Date().toISOString().slice(0, 10)} value={form.follow_up_on} onChange={(event) => setForm((previous) => ({ ...previous, follow_up_on: event.target.value }))} required /></label>}
        <p>You remain the owner of this next step. Recording an outcome does not send a reminder.</p>
        <div className="modal-actions"><button type="button" onClick={onClose}>Close</button><button type="submit" disabled={sending}>{sending ? "Saving…" : active ? "Record check result" : "Take this check"}</button></div>
      </form>
      {latest?.next_action === "propose_update" && <button type="button" className="signal-review-primary" onClick={onPropose}>Prepare an update for approval</button>}
      <details className="signal-review-history" open={data.state === "completed"}><summary>Your check history · {data.events.length} recorded events</summary><ol>{data.events.map((event) => <li key={event.revision}><strong>{event.state === "in_progress" ? "Taken by you" : reviewOptions.outcome[event.outcome]}</strong><span>{formatTime(event.recorded_at)}</span>{event.outcome && <><span>{reviewOptions.decision_impact[event.decision_impact]}</span><span>Cause: {reviewOptions.cause[event.cause]} · {reviewOptions.cause_status[event.cause_status]}</span><span>Sources checked: {event.evidence_ids.length ? event.evidence_ids.map((id) => `${data.sources.find((source) => source.id === id)?.label ?? id} · ${event.evidence_dates[id] || "date not recorded"}`).join("; ") : "No source reference recorded"}</span></>}<span>Next: {reviewOptions.next_action[event.next_action]}{event.follow_up_on ? ` · ${event.follow_up_on}` : ""}</span></li>)}</ol></details>
    </>}
  </section></div>;
}
