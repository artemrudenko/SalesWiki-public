#!/usr/bin/env python3
"""Permissioned-knowledge demo smoke test ("dry run").

Runs the whole demo end to end against a fresh, throwaway copy of the synthetic
permissioned vault and asserts every guarantee a reviewer would want to see live:
role-based read contrast + no-leak, the governed write loop (propose -> review ->
approve -> apply -> rollback), the reject path, and a tamper-evident audit chain.

Standard-library only (no MCP SDK needed): it drives the same role-bound tool
handlers the gateway exposes (`server.build_tools`) plus the single-writer worker.
It writes only into a temp directory, so it never touches the repo. Exit code 0 =
all checks passed (safe to run before a demo or in CI); non-zero = something to fix.

Usage:
    python3 scripts/demo_dryrun.py            # run, print report, exit 0/1
    python3 scripts/demo_dryrun.py --quiet    # only the final summary line
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config, server, worker  # noqa: E402
from saleswiki_mcp.audit import verify_chain  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

SECRETS = ("Discount floor", "Pricing:", "ACV", "internal budget", "RivalCorp")
RISK = "economic buyer"
UNPRIVILEGED = ["demo-broad-viewer", "demo-sam-sdr", "demo-olivia-marketing", "demo-hannah-legal"]
PRIVILEGED = ["demo-ethan-ae", "demo-claire-hos", "demo-raj-revops", "demo-sophie-curator", "demo-ada-admin"]
COMPANY = "BluePeak Energy"
COMPANY_ID = "demo-company-bluepeak-energy"


class Report:
    def __init__(self, quiet: bool) -> None:
        self.quiet = quiet
        self.failures: list[str] = []

    def check(self, label: str, ok: bool, detail: str = "") -> bool:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            self.failures.append(label)
        if not self.quiet:
            line = f"[{mark}] {label}"
            print(line if not detail else f"{line} — {detail}")
        return ok

    def section(self, title: str) -> None:
        if not self.quiet:
            print("\n" + title)


def run(quiet: bool) -> int:
    rep = Report(quiet)
    tmp = Path(tempfile.mkdtemp(prefix="demo-dryrun-"))
    vault = tmp / "permissioned"
    gdv.generate_permissioned_demo(vault)
    audit = tmp / "audit.jsonl"
    proposals = tmp / "proposals.jsonl"
    runtime = tmp / "runtime"
    # Anchor the audit clock to the (dynamic) generation date so timestamps track
    # the freshly stamped demo cards. Hours stay ordered for a monotonic chain.
    today = date.today().isoformat()
    def at(hour: int) -> str:
        return f"{today}T0{hour}:00:00Z"
    svc = build_default_service(vault, audit, proposals, now=lambda: at(0))

    def who(actor_id: str):
        return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()

    def tools(actor_id: str):
        return server.build_tools(svc, who(actor_id))

    read_tools = ["saleswiki.company_brief", "saleswiki.deal_risk", "saleswiki.call_prep",
                  "saleswiki.lead_priority", "saleswiki.event_brief", "saleswiki.campaign_brief",
                  "saleswiki.content_opportunities", "saleswiki.my_day", "saleswiki.pipeline_risk_digest"]

    def call(t, name):
        arg = {"saleswiki.company_brief": COMPANY, "saleswiki.call_prep": COMPANY,
               "saleswiki.event_brief": "Sales Tech Summit 2026", "saleswiki.campaign_brief": "Q3 ROI Push"}.get(name, "")
        return t[name](arg)["text"]

    # 1. No-leak: unprivileged roles never see sales-confidential secrets, any tool.
    rep.section("== Read contrast: no-leak for unprivileged roles ==")
    for role in UNPRIVILEGED:
        t = tools(role)
        leaked = [f"{n}:{s}" for n in read_tools for s in SECRETS if s in call(t, n)]
        rep.check(f"no secret leaks to {role}", not leaked, "; ".join(leaked))

    # 2. Privileged roles see deal risk; unprivileged do not.
    rep.section("== Deal-risk visibility by role ==")
    for role in PRIVILEGED:
        rep.check(f"{role} sees deal risk", RISK in tools(role)["saleswiki.deal_risk"]("")["text"])
    for role in UNPRIVILEGED:
        rep.check(f"{role} does NOT see deal risk", RISK not in tools(role)["saleswiki.deal_risk"]("")["text"])

    # 3. Access labels: marketing vs owner.
    rep.section("== Access labels ==")
    rep.check("deal_risk marketing=aggregated", svc.deal_risk(who("demo-olivia-marketing"), None)["access"] == "aggregated")
    rep.check("deal_risk owner=allowed", svc.deal_risk(who("demo-ethan-ae"), None)["access"] == "allowed")
    rep.check("company_brief owner sees pricing", any(s in tools("demo-ethan-ae")["saleswiki.company_brief"](COMPANY)["text"] for s in SECRETS))

    # 4. Business value: broad signals/proof for marketing, restricted competitor context for sales.
    rep.section("== Business value storyline ==")
    marketing_brief = tools("demo-olivia-marketing")["saleswiki.company_brief"](COMPANY)["text"]
    owner_brief = tools("demo-ethan-ae")["saleswiki.company_brief"](COMPANY)["text"]
    rep.check("marketing sees public-safe market signal", "cost-reduction initiative" in marketing_brief)
    rep.check("marketing sees sanitized ROI proof", "14 hours" in marketing_brief)
    rep.check("owner sees competitor intel", "RivalCorp" in owner_brief)
    rep.check("content opportunities include ROI proof gap", "ROI proof gap" in tools("demo-olivia-marketing")["saleswiki.content_opportunities"]("")["text"])

    # 5. Governed write loop.
    rep.section("== Governed write loop ==")
    msg = tools("demo-olivia-marketing")["saleswiki.request_redaction_review"](COMPANY_ID, "contact PII exposed")
    pid = "proposal-0001"
    rep.check("marketing can propose", pid in msg["text"] and msg["proposal_id"] == pid)
    rep.check("curator sees it in review_queue", pid in tools("demo-sophie-curator")["saleswiki.review_queue"]("")["text"])
    rep.check("sales role cannot approve", tools("demo-ethan-ae")["saleswiki.approve_proposal"](pid)["status"] == "blocked")
    rep.check("curator can approve", tools("demo-sophie-curator")["saleswiki.approve_proposal"](pid)["status"] == "approved")
    card = vault / "broad" / "wiki" / "entities" / "companies" / f"Company - {COMPANY}.md"
    rep.check("card unchanged before worker", "contact PII exposed" not in card.read_text(encoding="utf-8"))
    summary = worker.apply_approved(vault, proposals, audit, runtime, now=lambda: at(1))
    rep.check("worker applied the proposal", pid in summary["applied"])
    rep.check("applied note is on the card", "contact PII exposed" in card.read_text(encoding="utf-8"))
    rollback = worker.rollback(vault, proposals, audit, runtime, pid, now=lambda: at(2))
    rep.check("rollback restores the card", rollback["status"] == "rolled-back" and "contact PII exposed" not in card.read_text(encoding="utf-8"))

    # 6. Reject path never applies.
    rep.section("== Reject path ==")
    tools("demo-ethan-ae")["saleswiki.flag_stale_or_wrong"](COMPANY_ID, "stale")
    pid2 = "proposal-0002"
    rep.check("curator can reject", tools("demo-sophie-curator")["saleswiki.reject_proposal"](pid2, "not a real issue")["status"] == "rejected")
    summary2 = worker.apply_approved(vault, proposals, audit, runtime, now=lambda: at(3))
    rep.check("rejected proposal is never applied", pid2 not in summary2["applied"])

    # 6b. Governed ingest (Drive connector) rides the same propose->approve->apply loop.
    rep.section("== Governed ingest (Drive) ==")
    ipid = svc.ingest_resource(who("demo-ethan-ae"), COMPANY_ID,
                               "Drive gd-001: discovery transcript [synthetic]")
    rep.check("ingest proposal captured", ipid.startswith("proposal-"))
    tools("demo-sophie-curator")["saleswiki.approve_proposal"](ipid)
    isum = worker.apply_approved(vault, proposals, audit, runtime, now=lambda: at(4))
    rep.check("worker applies ingest to the card", ipid in isum["applied"])
    rep.check("ingest note lands in Review Needed", "Ingest proposed" in card.read_text(encoding="utf-8"))

    # 7. Tamper-evident audit chain.
    rep.section("== Audit integrity ==")
    rep.check("audit hash-chain is intact", verify_chain(audit))

    # 8. Answer Contract envelope on every read tool.
    rep.section("== Answer Contract envelope ==")
    keys = {"title", "access", "conclusion", "sections", "citations", "text"}
    access_ok = {"allowed", "sanitized", "aggregated", "blocked", "not-found", "ambiguous"}
    ethan = who("demo-ethan-ae")
    envelope_ok = True
    for name in (
        "company_brief", "deal_risk", "call_prep", "lead_priority",
        "event_brief", "campaign_brief", "content_opportunities",
        "my_day", "pipeline_risk_digest",
    ):
        arg = {"company_brief": COMPANY, "call_prep": COMPANY, "event_brief": "Sales Tech Summit 2026", "campaign_brief": "Q3 ROI Push"}.get(name)
        out = getattr(svc, name)(ethan, arg) if arg is not None else getattr(svc, name)(ethan)
        if not keys.issubset(out) or out["access"] not in access_ok:
            envelope_ok = False
    rep.check("every read tool returns the Answer envelope", envelope_ok)

    total = len(rep.failures)
    print("\n" + ("=" * 60))
    if total == 0:
        print("DEMO DRY RUN: ALL CHECKS PASSED — ready to demo.")
    else:
        print(f"DEMO DRY RUN: {total} CHECK(S) FAILED — {', '.join(rep.failures)}")
    return 1 if total else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Permissioned-knowledge demo smoke test.")
    parser.add_argument("--quiet", action="store_true", help="Only print the final summary line.")
    args = parser.parse_args()
    return run(args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
