import { useEffect, useState } from "react";
import { reviewOptions } from "../signalReviewClient.js";

export function SignalReviewStatus({ accountId, person, client, revision, onOpen }) {
  const [result, setResult] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    setResult(null);
    client.get({ target: accountId, signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted) setResult(value);
    }).catch(() => { if (!controller.signal.aborted) setResult({ status: "error" }); });
    return () => controller.abort();
  }, [accountId, person.id, client, revision]);
  const latest = result?.data?.events.at(-1);
  return <section className="personal-review-status" aria-label="Your context check">
    <strong>Your context check</strong>
    <p>{!result ? "Opening your check history…" : result.status !== "ready" ? "Check history is unavailable." : !latest ? "No personal check recorded." : latest.state === "in_progress" ? `In progress · ${person.name}` : `${reviewOptions.outcome[latest.outcome]} · ${person.name}`}</p>
    {latest && <p>Next: {reviewOptions.next_action[latest.next_action]}{latest.follow_up_on ? ` · ${latest.follow_up_on}` : ""}</p>}
    <button type="button" onClick={onOpen}>Check account context</button>
  </section>;
}
