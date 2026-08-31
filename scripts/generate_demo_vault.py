#!/usr/bin/env python3
"""Generate an isolated synthetic demo vault for SalesWiki presentations."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Stamp the demo with the generation date so cards labeled "freshness: fresh"
# are honestly fresh when regenerated before a demo, instead of advertising a
# frozen past date that looks like stale live data weeks later. Regenerate with
# `python3 scripts/generate_demo_vault.py --reset` before each presentation.
TODAY = date.today().isoformat()


def day(offset: int = 0) -> str:
    """A demo scenario date relative to the generation date. Forward-looking
    fields (next review, next check, deal close) stay near 'today' whenever the
    vault is regenerated, so they never read as overdue on a freshly stamped
    'fresh' card. Offsets preserve the original scenario spacing."""
    return (date.today() + timedelta(days=offset)).isoformat()


def safe_reset(path: Path) -> None:
    demo_root = (PROJECT_ROOT / "demo").resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(demo_root):
        raise ValueError(f"refusing to reset outside demo/: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def frontmatter(card_type: str, entity_id: str, extra: str, tags: list[str], access: str = "internal") -> str:
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    return f"""---
type: {card_type}
entity_id: {entity_id}
template_version: 1
dataset: demo
synthetic: true
created: {TODAY}
updated: {TODAY}
last_reviewed: {TODAY}
freshness: fresh
confidence: medium
access: {access}
profile_lock: locked
deletion_status: active
tags:
{tag_lines}
{extra.rstrip()}
---"""


def common_sections(change_source: str = "demo generator") -> str:
    return f"""
## Evidence

- Synthetic demo data only. Do not use for CRM, reporting or customer-facing claims.

## Review Needed

- Delete or regenerate this demo dataset when the presentation is complete.

## Change History

| Date | Change | Source/request |
| --- | --- | --- |
| {TODAY} | Created synthetic demo card | {change_source} |
"""


def company_card(name: str, slug: str, owner: str, status: str, segment: str, priority: str) -> str:
    extra = f"""status: {status}
owner: {owner}
last_checked: {TODAY}
next_check: {day(6)}
monitoring_status: active
monitoring_cadence: weekly
monitoring_owner: {owner}
website: https://example.invalid/{slug}
aliases:
  - {name}
"""
    return f"""{frontmatter("company", f"demo-company-{slug}", extra, ["company", "demo"])}

# Company: {name}

## Controlled Profile

- Website: https://example.invalid/{slug}
- Industry: {segment}
- ICP fit: {priority}
- Monitoring status: active
- Monitoring cadence: weekly
- Next check: {day(6)}

## Live Intelligence

{name} is a synthetic demo account used to show how SalesWiki connects account context, leads, deals, calls and next actions.

## Strategic Conclusions

- Current priority: {priority}
- Likely business pains: fragmented sales knowledge, slow follow-up and unclear campaign feedback.
- Buying triggers: recent growth signal, event activity or active evaluation.
- Best messaging angle: show how sales and marketing get one shared action layer.
- Main risks: no real stakeholder validation yet.
- Recommended owner action: review linked leads and tasks in Sales Today.
- Confidence: medium
- Evidence: synthetic demo cards only.

## Linked Entities

- Leads: [[Lead - {name} - Primary Buyer]]
- Deals: [[Deal - {name} - Pilot]] 
- Calls: [[Call - {name} - 2026-05-29 - Discovery]]

{common_sections()}"""


def person_card(name: str, slug: str, company: str, company_slug: str, role: str) -> str:
    extra = f"""status: active
owner: sales-demo
company: "[[Company - {company}]]"
aliases:
  - {name}
"""
    return f"""{frontmatter("person", f"demo-person-{slug}", extra, ["person", "demo"], access="sales-confidential")}

# Person: {name}

## Controlled Profile

- Company: [[Company - {company}]]
- Role: {role}
- LinkedIn: demo-only

## Live Intelligence

Synthetic stakeholder for demo walkthroughs.

## Relationship And Messaging Conclusions

- Likely priority: reduce manual sales coordination.
- Messaging angle: operational clarity and faster next actions.
- Relationship status: demo prospect.

## Linked Entities

- Company: [[Company - {company}]]
- Leads: [[Lead - {company} - Primary Buyer]]

{common_sections()}"""


def lead_card(company: str, slug: str, idx: int, owner: str, score: int, band: str, segment: str, due: str) -> str:
    extra = f"""lead_type: warm
pipeline_segment: {segment}
company: "[[Company - {company}]]"
owner: {owner}
source: demo-generated
last_touched: 2026-05-29
next_review: {due}
score: {score}
score_band: {band}
score_model: scoring-models-v1/mql
score_confidence: medium
scored_at: {TODAY}
score_decay:
freshness: needs-action
"""
    return f"""{frontmatter("lead", f"demo-lead-{slug}-{idx}", extra, ["lead", "demo"], access="sales-confidential")}

# Lead: {company} Primary Buyer {idx}

## Controlled Profile

- Company: [[Company - {company}]]
- Contact: [[Person - {company} Buyer]]

## Live Intelligence

Synthetic lead with a demo score and explicit next action.

## Score Readout

- Score: {score}
- Band: {band}
- Top positive factors: ICP fit, recent trigger, stakeholder relevance.
- Top risks: demo data only, no real source.
- Recommended next action: send contextual follow-up and update outcome.
- Owner: {owner}
- Next review: {due}

## Linked Entities

- Company: [[Company - {company}]]
- Tasks: [[Task - Follow Up - {company}]]

## Next Action

- Action: Follow up with a short trigger-based note.
- Due: {due}
- Owner: {owner}
- Related task: [[Task - Follow Up - {company}]]

{common_sections()}"""


def deal_card(company: str, slug: str, owner: str, score: int, band: str, stage: str, close_date: str) -> str:
    extra = f"""company: "[[Company - {company}]]"
owner: {owner}
stage: {stage}
amount: 25000
close_date: {close_date}
hubspot_object_type: deal
hubspot_id: demo-hs-deal-{slug}
crm_owner: {owner}
crm_stage: {stage}
crm_last_synced: {TODAY}
last_updated: 2026-05-29
score: {score}
score_band: {band}
score_model: scoring-models-v1/deal
score_confidence: medium
scored_at: {TODAY}
score_decay:
freshness: needs-action
"""
    return f"""{frontmatter("deal", f"demo-deal-{slug}-pilot", extra, ["deal", "demo"], access="sales-confidential")}

# Deal: {company} Pilot

## Controlled Profile

- Company: [[Company - {company}]]
- HubSpot deal: demo-hs-deal-{slug}
- CRM stage: {stage}
- CRM last synced: {TODAY}

## Live Intelligence

## Deal Readout

- Why now: synthetic pilot evaluation.
- Buyer priority: simplify sales/marketing knowledge flow.
- Champion strength: medium.
- Main risk: next step needs owner confirmation.
- Next best action: book follow-up and confirm success criteria.
- Confidence: medium
- Evidence: demo call and lead cards.

## Linked Entities

- Company: [[Company - {company}]]
- Leads: [[Lead - {company} - Primary Buyer 1]]
- Calls: [[Call - {company} - 2026-05-29 - Discovery]]

## Next Best Action

- Confirm evaluation criteria.
- Related task: [[Task - Deal Next Step - {company}]]
- Due: 2026-06-02
- Owner: {owner}

{common_sections()}"""


def call_card(company: str, slug: str, owner: str) -> str:
    extra = f"""source_id: demo-call-{slug}
raw_path: raw/calls/{slug}-discovery.txt
content_hash: demo-only
ingest_run_id: demo-seed-2026-05-30
company: "[[Company - {company}]]"
deal: "[[Deal - {company} - Pilot]]"
date: 2026-05-29
participants:
  - "[[Person - {company} Buyer]]"
participant_match_status: medium
transcript: raw/calls/{slug}-discovery.txt
recording:
transcript_status: available
language: en
analyst: demo-agent
"""
    return f"""{frontmatter("call", f"demo-call-{slug}-discovery", extra, ["call", "demo"], access="sales-confidential")}

# Call: {company} / 2026-05-29 / Discovery

## Controlled Profile

- Google Meet recording: demo-only
- Google Meet transcript: raw/calls/{slug}-discovery.txt
- HubSpot activity: demo-only

## Executive Summary

- Buyer wants a clearer handoff between marketing research and sales action.
- Main pain is stale information before outreach.
- Follow-up should include a short dashboard walkthrough.

## Linked Entities

- Company: [[Company - {company}]]
- Deal: [[Deal - {company} - Pilot]]
- Participants: [[Person - {company} Buyer]]
- Follow-up tasks: [[Task - Follow Up - {company}]]

## Buying Signals

| Signal | Evidence from call | Strength |
| --- | --- | --- |
| Dashboard interest | Asked to see daily priority view | high |

## Sanitized Summary

- Approved for broad sharing: yes
- Personal data removed: yes
- Safe summary: Synthetic discovery call for demo.
- Reviewer: demo-agent

{common_sections()}"""


def task_card(title: str, slug: str, related: str, owner: str, due: str, priority: str) -> str:
    extra = f"""status: open
task_type: follow-up
owner: {owner}
due: {due}
priority: {priority}
related_entity: "[[{related}]]"
source: demo-generated
freshness: needs-action
"""
    return f"""{frontmatter("task", f"demo-task-{slug}", extra, ["task", "demo"], access="internal")}

# Task: {title}

## Controlled Profile

- Owner: {owner}
- Due: {due}
- Priority: {priority}
- Related entity: [[{related}]]

## Action

- What to do: {title}
- Why: Demonstrates how Sales Today turns knowledge into work.
- Expected output: logged outcome and next step.
- Source/evidence: demo cards.
- Duplicate check: demo-only.

## Linked Entities

- Related: [[{related}]]

## Result

- Status: open
- Completed:
- Outcome:
- Next task:

{common_sections()}"""


def knowledge_card(card_type: str, folder: str, title: str, entity_id: str, status: str, owner: str) -> tuple[str, str]:
    extra = f"""status: {status}
owner: {owner}
next_check: {day(11)}
freshness: needs-action
"""
    content = f"""{frontmatter(card_type, entity_id, extra, [card_type, "demo"])}

# {title}

## Controlled Profile

- Owner: {owner}
- Status: {status}

## Live Intelligence

Synthetic marketing insight for demo dashboards.

## Linked Entities

- Companies: [[Company - Orion Foods]], [[Company - Atlas Robotics]]
- Campaign: [[Campaign - Demo ABM Sprint]]

{common_sections()}"""
    return folder, content


def source_card(title: str, slug: str) -> str:
    extra = f"""source_id: demo-source-{slug}
raw_path: raw/research/{slug}.md
content_hash: demo-only
ingest_run_id: demo-seed-2026-05-30
source_type: research-note
date_collected: {TODAY}
freshness: fresh
"""
    return f"""{frontmatter("source", f"demo-source-{slug}", extra, ["source", "demo"])}

# Source: {title}

## Controlled Profile

- Source type: research-note
- Raw path: raw/research/{slug}.md

## Source Summary

Synthetic research note used to demonstrate evidence handling.

## Linked Entities

- Companies: [[Company - Orion Foods]]

{common_sections()}"""


def perm_frontmatter(card_type: str, entity_id: str, boundary: str, access: str, extra_lines: list[str], tags: list[str]) -> str:
    """Frontmatter for permissioned demo cards. `boundary` records the physical boundary folder."""
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    extra = "\n".join(extra_lines)
    return f"""---
type: {card_type}
entity_id: {entity_id}
template_version: 1
dataset: demo
synthetic: true
created: {TODAY}
updated: {TODAY}
last_reviewed: {TODAY}
freshness: fresh
confidence: medium
access: {access}
boundary: {boundary}
profile_lock: locked
deletion_status: active
tags:
{tag_lines}
{extra}
---"""


# Per-account engagement metrics (broad zone: safe for every role). The visit
# trends deliberately tell each account's story — Solara declines (renewal at
# risk), Ironclad climbs (post-pilot expansion).
PERMISSIONED_ENGAGEMENT: dict[str, dict] = {
    "bluepeak-energy": {"visits": [12, 15, 14, 19, 24, 28, 31, 37], "calls_held": 6, "calls_planned": 2},
    "northstar-robotics": {"visits": [9, 11, 14, 13, 17, 19, 22, 24], "calls_held": 5, "calls_planned": 1},
    "atlas-foods": {"visits": [8, 9, 7, 10, 9, 11, 10, 12], "calls_held": 3, "calls_planned": 1},
    "meridian-payments": {"visits": [21, 25, 24, 30, 34, 39, 45, 52], "calls_held": 8, "calls_planned": 3},
    "cedar-health": {"visits": [11, 13, 12, 16, 15, 18, 21, 23], "calls_held": 4, "calls_planned": 2},
    "solara-hospitality": {"visits": [34, 30, 27, 22, 18, 15, 12, 9], "calls_held": 2, "calls_planned": 1},
    "ironclad-freight": {"visits": [6, 8, 13, 18, 26, 33, 41, 48], "calls_held": 7, "calls_planned": 3},
}


def perm_company_broad(name: str, slug: str, *, industry: str = "synthetic demo segment",
                       icp: str = "high", summary: str = "", public_angle: str = "",
                       signal_title: str = "", has_deal: bool = True, status: str = "target") -> str:
    fm = perm_frontmatter(
        "company", f"demo-company-{slug}", "broad", "internal",
        ["owner: demo-curator", f"status: {status}"], ["company", "demo"],
    )
    summary = summary or f"{name} is a synthetic permissioned-demo account. This broad card is the sanitized summary every employee may see."
    public_angle = public_angle or "For deal specifics, see the sales-owner view."
    signal_link = f"\n- Market signal: [[Source - {signal_title}]]" if signal_title else ""
    # Prospects (top-of-funnel) have no deal yet — omit the dangling deal link.
    deal_link = f"- Deal (sales-confidential): [[Deal - {name} - Pilot]]\n" if has_deal else ""
    eng = PERMISSIONED_ENGAGEMENT.get(slug)
    engagement_section = ""
    if eng:
        visits = ", ".join(str(v) for v in eng["visits"])
        engagement_section = f"""## Engagement Snapshot

- Weekly site visits (last {len(eng['visits'])} weeks): {visits}
- Calls held this quarter: {eng['calls_held']}
- Calls planned: {eng['calls_planned']} (next: {day(3)})
- 🤖 Tracked by the connector-sync agent (synthetic); demo numbers.

"""
    body = f"""
# Company: {name}

## Controlled Profile

- Industry: {industry}
- ICP fit: {icp}

## Live Intelligence

{summary}

## Strategic Conclusions

- {public_angle}
- Note: pricing, competitor and deal economics are sales-confidential and shown only to authorized roles.
- Confidence: medium
- Evidence: synthetic demo only.

{engagement_section}## Linked Entities

{deal_link}- Lead: [[Lead - {name}]]{signal_link}

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def _deal_band(score: int) -> str:
    """Derive a readable deal-score band from the numeric score."""
    return "high" if score >= 80 else "medium" if score >= 65 else "low"


def perm_deal_salesconf(name: str, slug: str, owner_actor: str, team: str, *,
                        acv: str = "$240k", floor: str = "18%", champion: str = "VP Operations",
                        eb: str = "not yet engaged", stage: str = "Proposal",
                        score: int = 74, win_probability: str = "55%", days_in_stage: int = 21,
                        risk: str = "stale next step; economic buyer not yet engaged.",
                        action: str = "confirm the next step and protect the discount floor.",
                        pricing_note: str = "buyer pushing for an annual discount") -> str:
    fm = perm_frontmatter(
        "deal", f"demo-deal-{slug}-pilot", "sales-confidential", "sales-confidential",
        [f"company: demo-company-{slug}", f"owner: {owner_actor}", f"team: {team}", f"stage: {stage}"],
        ["deal", "demo"],
    )
    body = f"""
# Deal: {name} - Pilot

## Controlled Profile

- Company: [[Company - {name}]]
- Owner: {owner_actor}
- Team: {team}
- Stage: {stage}

## Live Intelligence

Sales-confidential deal context for {name}. Visible only to the assigned sales owner / team, HoS, RevOps and curators.

## Current State

- Active negotiation in the {stage} stage.

## Deal Readout

- Pricing: {acv} ACV proposed; Discount floor: {floor} (do not exceed without HoS sign-off).
- Negotiation note: {pricing_note}; champion is {champion}.

## Scoring

- Score: {score}
- Win probability: {win_probability}
- ACV: {acv}
- Days in stage: {days_in_stage}
- Score band: {_deal_band(score)}

## Buying Committee

- Champion: {champion}
- Economic buyer: {eb}

## Timeline

- Close target: this quarter.

## Calls and Notes

- See linked discovery call.

## Risks

- Risk: {risk}

## Next Best Action

- Recommended action: {action}

## Linked Entities

- Company: [[Company - {name}]]

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_call_salesconf(name: str, slug: str, owner_actor: str, team: str, *,
                        summary: str = "", signals: str = "", risk_detail: str = "",
                        action: str = "", pain: str = "", objection: str = "",
                        commitment: str = "") -> str:
    """Sales-confidential Call card: sanitized conclusions only.

    The raw transcript and recording never live here - they stay an opaque
    personal-data handle, so even an authorized sales reader gets the sanitized
    takeaway plus a `restricted://` reference, never the raw body.
    """
    handle = f"restricted://personal-data/demo-{slug}-callrecording"
    summary = summary or "champion engaged; technical validation positive; next call should focus on ROI."
    signals = signals or "Technical validation positive; champion engaged."
    risk_detail = risk_detail or "prospect named internal budget near the floor and that the incumbent vendor is RivalCorp."
    action = action or "prep an ROI-focused follow-up and protect the discount floor."
    # LLM-extracted, sanitized (no pricing/competitor/budget — those stay in the
    # competitor-intel card and the personal-data transcript).
    pain = pain or "manual reporting/evidence effort each cycle slows the team"
    objection = objection or "needs finance buy-in before committing to a pilot"
    commitment = commitment or "champion to schedule a technical validation session"
    fm = perm_frontmatter(
        "call", f"demo-call-{slug}-discovery", "sales-confidential", "sales-confidential",
        [f"company: demo-company-{slug}", f"owner: {owner_actor}", f"team: {team}", "call_date: " + TODAY],
        ["call", "demo"],
    )
    body = f"""
# Call: {name} - Discovery

## Controlled Profile

- Company: [[Company - {name}]]
- Owner: {owner_actor}
- Team: {team}
- Raw transcript: {handle}

## Executive Summary

- Sanitized takeaway: {summary}
- 🤖 Extracted from the call by the call-analyst agent (synthetic): pain — {pain}; objection — {objection}; commitment — {commitment}.

## Customer Context

Sanitized sales-call summary for {name}. Visible only to assigned sales, HoS,
RevOps and curators. The raw transcript stays in controlled personal-data
storage and is referenced only by the handle above.

## Buying Signals

- {signals}
- 🤖 Detected intent (synthetic): evaluating now, comparing alternatives, ROI is the decision driver.

## Objections and Risks

- Objection (extracted): {objection}.
- {risk_detail}

## Commitments

- {commitment}.
- Follow-up call to be scheduled.

## Follow-Up Draft

- Recommended action: {action}

## Linked Entities

- Company: [[Company - {name}]]

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


# "Role (Name[, Title])? :" speaker tag at the start of a transcript line.
_SPEAKER_LINE = re.compile(r"^(?P<role>[^:()]+?)(?:\s*\((?P<paren>[^)]*)\))?:\s")


def _sanitized_call_extract(transcript: str) -> str:
    """Reduce a raw speaker-attributed transcript (generator input only — it never
    lands on a card) to sanitized metadata bullets: participant roles with the
    names redacted (titles kept), the exchange length, and an explicit redaction
    note. The boundary registry declares `raw_bodies_allowed: false` for
    personal-data, so cards there carry handles + sanitized extracts, never the
    raw body (see permissioned-knowledge security review)."""
    labels: dict[str, str] = {}  # speaker role -> best label (a titled one wins)
    order: list[str] = []
    turns = 0
    for line in transcript.splitlines():
        match = _SPEAKER_LINE.match(line.strip())
        if not match:
            continue
        turns += 1
        role = match.group("role").strip()
        paren = (match.group("paren") or "").strip()
        # "Champion (Dana Reyes, VP Operations)" -> keep the title, drop the name.
        title = paren.split(",", 1)[1].strip() if "," in paren else ""
        if role not in labels:
            labels[role] = f"{role} ({title})" if title else role
            order.append(role)
        elif title and labels[role] == role:
            labels[role] = f"{role} ({title})"  # later titled mention upgrades it
    who = "; ".join(labels[r] for r in order) if order else "not recorded"
    return (
        f"- Participants (roles only, identities REDACTED): {who}\n"
        f"- Exchange length: {turns} speaker turns\n"
        "- Direct quotes, contact identities and commercial figures: REDACTED — "
        "readable only through the raw source behind the opaque handle above "
        "(admin or an approved, time-boxed access grant; every read is audited)."
    )


def perm_personaldata_ref(name: str, slug: str, *, transcript: str = "") -> str:
    """Personal-data reference card: opaque handle + clearly-marked SANITIZED
    extraction. The raw speaker-attributed transcript never lands in the card
    body — `raw_bodies_allowed: false` in schemas/boundary-registry.json (and the
    health check enforces it)."""
    handle = f"restricted://personal-data/demo-{slug}-discovery"
    fm = perm_frontmatter(
        "personal-data-ref", f"demo-pdref-{slug}-discovery", "personal-data", "personal-data",
        [f"company: demo-company-{slug}", f"restricted_ref: {handle}"],
        ["call", "demo", "personal-data"],
    )
    extract_block = (
        f"\n## Sanitized Extract (no raw quotes)\n\n"
        f"> SANITIZED: structured extraction from the discovery call. Speaker "
        f"identities, direct quotes and unredacted figures are removed by contract "
        f"(`raw_bodies_allowed: false`); the raw source stays behind the handle above.\n\n"
        f"{_sanitized_call_extract(transcript)}\n"
        if transcript else ""
    )
    body = f"""
# Personal-Data Reference: {name} Discovery Call

## Controlled Profile

- Company: [[Company - {name}]]
- Handle: {handle}

## Live Intelligence

This card lives outside the broad vault in the controlled personal-data boundary. Access requires explicit approval and is audited; unauthorized roles see only the opaque handle above.
{extract_block}
{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_lead_broad(name: str, slug: str, band: str, source: str, why: str,
                    score: int = 80, stage: str = "SQL",
                    next_action: str = "book a discovery call this week.") -> str:
    """Broad lead card: score, band, funnel stage and "why now" are shared with
    sales and marketing; the lead contact stays an opaque personal-data handle.
    """
    handle = f"restricted://personal-data/demo-{slug}-lead-contact"
    fm = perm_frontmatter(
        "lead", f"demo-lead-{slug}", "broad", "internal",
        [f"company: demo-company-{slug}", "owner: demo-sdr", f"score_band: {band}", f"source: {source}"],
        ["lead", "demo"],
    )
    body = f"""
# Lead: {name}

## Controlled Profile

- Company: [[Company - {name}]]
- Contact: {handle}
- Source: {source}

## Live Intelligence

Marketing-qualified lead for {name}. The score band and "why now" are shared
with both sales and marketing; the contact identity is a personal-data handle.

## Why This Lead Matters

- Why now: {why}

## Scoring

- Score: {score}
- Score band: {band}
- Funnel stage: {stage}
- 🤖 Scored by the lead-scoring agent (synthetic) on {TODAY} · model: scoring-models-v1/mql · confidence: medium.
- Top positive factors: ICP fit, recent buying-intent activity, stakeholder relevance.
- Top risk: synthetic demo data — not yet corroborated by a verified source.

## Outreach Context

- Source: {source}

## Activity

- 2026-05-22: first touch via {source}.
- 2026-05-27: {why}
- 2026-05-29: routed for prioritization by the lead-monitor agent (synthetic).

## Next Action

- Recommended action: {next_action}

## Linked Entities

- Company: [[Company - {name}]]

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_event_broad(companies: list[tuple]) -> str:
    """Broad event card linking target accounts. Public-safe; deal detail per
    account is resolved per-role by event_brief, not stored here.
    """
    fm = perm_frontmatter(
        "event", "demo-event-sales-tech-summit-2026", "broad", "internal",
        ["event_date: 2026-09-15", "event_type: conference"],
        ["event", "demo"],
    )
    targets = "\n".join(f"- [[Company - {name}]]" for name, *_ in companies)
    body = f"""
# Event: Sales Tech Summit 2026

## Controlled Profile

- Event date: 2026-09-15
- Event type: conference

## Live Intelligence

Sales Tech Summit 2026 is a synthetic permissioned-demo event. The target-account
list below is public-safe; private deal context per account is added per-role by
event_brief and is never stored on this broad card.

## Why It Matters

- Multiple target accounts attending.

## Target Accounts Present

{targets}

## Outreach Opportunities

- Content angle: ROI and time-to-value story for the target segment.
- Recommended action: prep an account-specific outreach plan before the event.

## Linked Entities

- Target accounts listed above.

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_painpoint_broad(title: str, slug: str, angle: str, asset: str) -> str:
    """Broad marketing pain-point card: public-safe content angle + suggested asset."""
    fm = perm_frontmatter(
        "pain-point", f"demo-pain-{slug}", "broad", "internal",
        ["status: active"], ["pain-point", "demo"],
    )
    body = f"""
# Pain Point: {title}

## Controlled Profile

- Pain: {title}

## Problem Definition

- {title}

## Symptoms

- Reported by buyers in the target segment.

## Impact

- Material cost and risk for the buyer.

## Who Cares

- Operations and finance buyers.

## Messaging

- Content angle: {angle}
- Suggested asset: {asset}

## Discovery Questions

- How do you handle {title} today?

## Related Use Cases

- See linked campaigns.

## Linked Entities

- Related companies and campaigns.

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_market_signal_broad(name: str, slug: str, *, signal_title: str = "",
                             signal_phrase: str = "cost-reduction initiative",
                             signal_sentence: str = "", signal_slug: str = "cost-reduction-signal") -> str:
    """Broad market signal: fresh, public-safe account trigger for company_brief."""
    signal_title = signal_title or f"{name} Cost Reduction Signal"
    signal_sentence = signal_sentence or (
        f"{name} launched a cost-reduction initiative and is asking operations teams to "
        f"quantify time-to-value before the next quarterly planning cycle.")
    fm = perm_frontmatter(
        "source", f"demo-source-{slug}-{signal_slug}", "broad", "internal",
        [f"company: demo-company-{slug}", "source_type: synthetic-market-signal"],
        ["source", "demo", "news"],
    )
    body = f"""
# Source: {signal_title}

## Controlled Profile

- Company: [[Company - {name}]]
- Source type: synthetic market signal

## Live Intelligence

Public-safe signal: {signal_sentence} This makes ROI proof and implementation speed the strongest outreach angle.
🤖 Detected by the research agent (synthetic) on 2026-05-28 · source: public web/news monitoring · confidence: medium.
Why it matters: aligns with an active buying trigger — lead with ROI proof while the window is open.

## Signal Detection (synthetic)

- Detected by: research agent · 2026-05-28
- Source: public web/news monitoring · corroboration: 1 source
- Confidence: medium (needs a second corroborating source to raise)
- Suggested action: tie outreach to this trigger before the next planning cycle.

## Source Summary

- Signal: {signal_phrase}.
- Sales relevance: connect ROI calculator, implementation proof and event follow-up.
- Marketing relevance: prioritize time-to-value content for this segment.

## Linked Entities

- Company: [[Company - {name}]]
- Campaign: [[Campaign - Q3 ROI Push]]

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_private_case_broad(name: str, slug: str, *, roi_proof: str = "",
                            roi_pain: str = "Manual reporting overhead", lesson: str = "") -> str:
    """Broad sanitized proof: shows reusable value without sensitive details."""
    roi_proof = roi_proof or ("a similar operations team cut weekly manual reporting effort by "
                              "14 hours and reached first measurable value inside 30 days.")
    lesson = lesson or "lead with implementation speed, not feature depth."
    fm = perm_frontmatter(
        "private-case", f"demo-private-case-{slug}-sanitized-proof", "broad", "internal",
        [f"company: demo-company-{slug}", "status: sanitized"],
        ["private-case", "case-study", "demo"],
    )
    body = f"""
# Private Case: {name} - Sanitized ROI Proof

## Controlled Profile

- Company: [[Company - {name}]]
- Status: sanitized

## Live Intelligence

Sanitized proof for broad use: {roi_proof}
Sensitive customer names, contract terms and implementation details are removed.

## Sanitized Summary

- Reusable lesson: {lesson}
- Proof level: internal sales and marketing use only.
- Removed: customer identity, commercial terms and direct transcript excerpts.

## Linked Entities

- Company: [[Company - {name}]]
- Pain Point: [[Pain Point - {roi_pain}]]

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_competitor_intel_salesconf(name: str, slug: str, owner_actor: str, team: str, *,
                                    competitor: str = "RivalCorp", comp_note: str = "") -> str:
    """Sales-confidential competitor note: valuable for sales, hidden from marketing."""
    comp_note = comp_note or (
        f"the champion says {competitor} is the incumbent vendor, but the buying committee is "
        f"frustrated by slow reporting configuration and weak ROI visibility.")
    comp_slug = re.sub(r"[^a-z0-9]+", "-", competitor.lower()).strip("-")
    fm = perm_frontmatter(
        "competitor-intel", f"demo-competitor-{slug}-{comp_slug}", "sales-confidential", "sales-confidential",
        [f"company: demo-company-{slug}", f"owner: {owner_actor}", f"team: {team}", f"competitor: {competitor}"],
        ["competitor-intel", "demo"],
    )
    body = f"""
# Competitor Intel: {name} - {competitor}

## Controlled Profile

- Company: [[Company - {name}]]
- Competitor: {competitor}
- Owner: {owner_actor}
- Team: {team}

## Live Intelligence

{comp_note} Do not mention this outside the account team.

## Strategic Conclusions

- Position against {competitor} on time-to-value and reporting automation.
- Bring the sanitized 30-day ROI proof, not a generic product deck.
- Keep pricing and incumbent detail restricted to the sales team.

## Linked Entities

- Company: [[Company - {name}]]
- Deal: [[Deal - {name} - Pilot]]

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


def perm_campaign_broad(companies: list[tuple]) -> str:
    """Broad campaign card linking target accounts; deal context is added per-role
    by campaign_brief, never stored here.
    """
    fm = perm_frontmatter(
        "campaign", "demo-campaign-q3-roi-push", "broad", "internal",
        ["status: active", "channel: email-and-events"], ["campaign", "demo"],
    )
    targets = "\n".join(f"- [[Company - {name}]]" for name, *_ in companies)
    body = f"""
# Campaign: Q3 ROI Push

## Controlled Profile

- Status: active
- Channel: email and events

## Goal

- Drive ROI-led pipeline in the target segment.

## Target Accounts And Leads

{targets}

## Messaging

- Content angle: ROI and time-to-value proof for the target segment.
- Email angle: "show measurable value before quarterly planning."
- Event follow-up angle: invite target accounts to compare their reporting
  workload against the sanitized 30-day proof.
- Asset sequence: ROI calculator -> sanitized proof -> account-specific follow-up.

## Performance

- (synthetic demo; no live metrics.)

## Learnings

- (synthetic demo.)

## Sales Handoff

- Recommended action: align outreach with each account's stage before send.

## Linked Entities

- Target accounts listed above.

{common_sections("permissioned demo generator")}"""
    return fm + "\n" + body


# slug -> (title, content angle, suggested asset) for broad marketing pain points.
PERMISSIONED_PAINS = {
    "energy-cost-volatility": ("Energy cost volatility", "show predictable spend with our pricing model", "ROI calculator"),
    "manual-reporting-overhead": ("Manual reporting overhead", "quantify hours saved by automation", "before/after case study"),
    "roi-proof-gap": ("ROI proof gap", "help champions justify the business case before finance review", "one-page ROI proof brief"),
    "incumbent-switching-cost": ("Incumbent switching cost", "de-risk the switch with a 30-day implementation plan", "migration checklist"),
    "compliance-reporting-burden": ("Compliance reporting burden", "cut audit-prep hours with automated evidence", "compliance automation brief"),
    "fraud-and-dispute-load": ("Fraud and dispute load", "show faster reconciliation and dispute resolution", "fraud-ops ROI brief"),
    "clinician-admin-overload": ("Clinician admin overload", "free clinician hours from manual reporting", "care-ops time-savings study"),
}


# Seven fully-fleshed synthetic accounts across distinct industries. Each profile
# drives a full card set (company / deal / call / lead / market signal / private
# case / competitor intel / personal-data ref) so every company can be
# explored from every angle. BluePeak keeps the exact strings the demo/tests assert.
# Solara Hospitality is the renewal-at-risk story (champion departed, save play);
# Ironclad Freight is the closed-won-pilot expansion story (quantified proof).
PERMISSIONED_PROFILES = [
    {
        "name": "BluePeak Energy", "slug": "bluepeak-energy", "owner": "demo-ivan-ae", "team": "sales-west",
        "industry": "Energy & utilities", "icp": "high",
        "summary": "BluePeak Energy is a synthetic permissioned-demo account. This broad card is the sanitized summary every employee may see.",
        "public_angle": "Cost-reduction buyer — lead outreach with ROI proof and time-to-value; deal specifics in the sales-owner view.",
        "signal": {"title": "BluePeak Energy Cost Reduction Signal", "phrase": "cost-reduction initiative",
                   "slug": "cost-reduction-signal",
                   "sentence": "BluePeak Energy launched a cost-reduction initiative and is asking operations teams to quantify time-to-value before the next quarterly planning cycle."},
        "roi": {"proof": "a similar operations team cut weekly manual reporting effort by 14 hours and reached first measurable value inside 30 days.",
                "pain": "Manual reporting overhead", "lesson": "lead with implementation speed, not feature depth."},
        "competitor": {"name": "RivalCorp", "note": "the champion says RivalCorp is the incumbent vendor, but the buying committee is frustrated by slow reporting configuration and weak ROI visibility."},
        "deal": {"acv": "$240k", "floor": "18%", "champion": "VP Operations", "eb": "not yet engaged",
                 "stage": "Proposal", "score": 74, "win_probability": "55%", "days_in_stage": 21,
                 "risk": "stale next step; economic buyer not yet engaged.",
                 "action": "confirm the next step and protect the discount floor.",
                 "pricing_note": "buyer pushing for an annual discount"},
        "call": {"summary": "champion engaged; technical validation positive; next call should focus on ROI.",
                 "signals": "Technical validation positive; champion engaged.",
                 "risk_detail": "prospect named internal budget near the floor and that the incumbent vendor is RivalCorp.",
                 "action": "prep an ROI-focused follow-up and protect the discount floor."},
        "lead": {"band": "hot", "stage": "SQL", "score": 88, "source": "Webinar: Energy ROI", "why": "downloaded the pricing guide twice this week",
                 "next": "scope the 30-day ROI pilot on their reporting workflow."},
        "transcript": (
            "AE (Ivan Petrov): Thanks for the time. What's driving the cost-reduction initiative right now?\n"
            "Champion (Dana Reyes, VP Operations): Finance wants every ops team to show time-to-value before Q3 planning. Weekly reporting eats two analyst-days.\n"
            "AE: If that dropped under an hour, what changes for you?\n"
            "Champion: I redeploy an analyst and can actually defend the budget. RivalCorp is our incumbent but their reporting config is painful.\n"
            "AE: Where is the internal budget landing?\n"
            "Champion: Near the floor — about $200-240k if I can prove 30-day value. Keep that between us.\n"
            "AE: Understood. Next step: a 30-day ROI pilot scoped to your reporting workflow?\n"
            "Champion: Yes — loop me before procurement talks pricing."
        ),
    },
    {
        "name": "Northstar Robotics", "slug": "northstar-robotics", "owner": "demo-maria-ae", "team": "sales-east",
        "industry": "Industrial robotics", "icp": "high",
        "summary": "Northstar Robotics builds factory-floor automation lines. This broad card is the sanitized summary every employee may see.",
        "public_angle": "Strong technical buyer — lead with changeover ROI; deal economics in the sales-owner view.",
        "signal": {"title": "Northstar Robotics Automation Expansion", "phrase": "automation expansion program",
                   "slug": "automation-expansion",
                   "sentence": "Northstar Robotics kicked off an automation expansion program and wants measurable changeover-time gains before adding new lines."},
        "roi": {"proof": "a similar manufacturer reduced line-changeover time by 9 hours per week and hit first value in under a month.",
                "pain": "Manual reporting overhead", "lesson": "anchor on throughput gains the plant manager already tracks."},
        "competitor": {"name": "MechRival", "note": "the plant team uses MechRival for line monitoring but complains it cannot tie changeover data to ROI for finance."},
        "deal": {"acv": "$310k", "floor": "15%", "champion": "Director of Manufacturing", "eb": "engaged (VP Plant Ops)",
                 "stage": "Proposal", "score": 81, "win_probability": "60%", "days_in_stage": 14,
                 "risk": "competitive pressure from MechRival; needs a clear changeover ROI story.",
                 "action": "send the changeover ROI comparison and lock a pilot scope.",
                 "pricing_note": "buyer comparing against incumbent renewal"},
        "call": {"summary": "strong technical fit; plant manager wants changeover ROI proof before committing.",
                 "signals": "Plant manager actively measuring changeover time; budget owner on the call.",
                 "risk_detail": "buyer hinted budget is set against the MechRival renewal quote and shared internal throughput targets.",
                 "action": "lead with the changeover ROI comparison versus MechRival."},
        "lead": {"band": "warm", "stage": "SQL", "score": 72, "source": "Event: RoboExpo booth scan", "why": "visited the booth and requested a follow-up",
                 "next": "send the changeover ROI comparison and book plant-floor time."},
        "transcript": (
            "AE (Maria Lopez): How is the automation expansion going?\n"
            "Champion (Sven Holt, Director of Manufacturing): Two new lines this year, but I can't add them until changeover time drops.\n"
            "AE: What does a good outcome look like?\n"
            "Champion: Cut changeover by a third. MechRival monitors the lines but I can't show finance the ROI.\n"
            "Economic Buyer (Priya N., VP Plant Ops): If you can quantify the throughput gain, I have budget against the MechRival renewal.\n"
            "AE: We can scope a pilot on one line and measure changeover directly.\n"
            "Champion: Do that — send the comparison and I'll get you floor time."
        ),
    },
    {
        "name": "Atlas Foods", "slug": "atlas-foods", "owner": "demo-ivan-ae", "team": "sales-west",
        "industry": "Food manufacturing", "icp": "medium",
        "summary": "Atlas Foods runs multi-plant food production. This broad card is the sanitized summary every employee may see.",
        "public_angle": "Compliance-driven buyer — lead with audit-readiness; commercial detail in the sales-owner view.",
        "signal": {"title": "Atlas Foods Quality Compliance Audit", "phrase": "quality-compliance audit",
                   "slug": "compliance-audit",
                   "sentence": "Atlas Foods is preparing for a quality-compliance audit and wants to cut the manual evidence-gathering effort each cycle."},
        "roi": {"proof": "a similar plant cut compliance reporting prep by 11 hours per audit cycle and standardized evidence across sites.",
                "pain": "Compliance reporting burden", "lesson": "tie the value to audit readiness, not generic dashboards."},
        "competitor": {"name": "FoodChain Systems", "note": "the quality team runs FoodChain Systems for traceability but rebuilds audit evidence by hand every cycle."},
        "deal": {"acv": "$180k", "floor": "20%", "champion": "Plant Operations Lead", "eb": "not yet engaged",
                 "stage": "Qualification", "score": 58, "win_probability": "35%", "days_in_stage": 9,
                 "risk": "early stage; economic buyer in finance not yet looped in.",
                 "action": "secure a compliance-readiness workshop to reach the economic buyer.",
                 "pricing_note": "price-sensitive, multi-site rollout potential"},
        "call": {"summary": "clear compliance pain; champion needs finance buy-in before a pilot.",
                 "signals": "Champion mapped the audit workflow; multi-site expansion possible.",
                 "risk_detail": "champion shared the audit timeline and that finance caps new tooling spend this quarter.",
                 "action": "package a compliance-readiness workshop and a phased multi-site price."},
        "lead": {"band": "warm", "stage": "SQL", "score": 70, "source": "Content: ROI calculator", "why": "completed the ROI calculator and opened two emails",
                 "next": "offer a compliance-readiness workshop slot before the audit."},
        "transcript": (
            "AE (Ivan Petrov): What's the priority before the audit?\n"
            "Champion (Grace Okoro, Plant Operations Lead): We rebuild audit evidence by hand every cycle — it's days of work across sites.\n"
            "AE: If evidence were continuous and standardized, what would that unlock?\n"
            "Champion: Faster audits and fewer findings. FoodChain handles traceability but not the audit packet.\n"
            "AE: Who signs off on new tooling?\n"
            "Champion: Finance — and they're tight this quarter, so I need a strong ROI story first.\n"
            "AE: Let's run a compliance-readiness workshop and phase the rollout by site."
        ),
    },
    {
        "name": "Meridian Payments", "slug": "meridian-payments", "owner": "demo-ivan-ae", "team": "sales-west",
        "industry": "Fintech & payments", "icp": "high",
        "summary": "Meridian Payments processes card and dispute flows for online merchants. This broad card is the sanitized summary every employee may see.",
        "public_angle": "Security-conscious buyer — lead with PCI/fraud-ops ROI; commercial detail in the sales-owner view.",
        "signal": {"title": "Meridian Payments Fraud-Ops Efficiency Review", "phrase": "fraud-ops efficiency review",
                   "slug": "fraud-ops-review",
                   "sentence": "Meridian Payments started a fraud-ops efficiency review after manual reconciliation and dispute handling fell behind transaction growth."},
        "roi": {"proof": "a similar payments team cut manual reconciliation effort by 16 hours per week and shortened dispute resolution time.",
                "pain": "Fraud and dispute load", "lesson": "lead with reconciliation hours and dispute SLA, not feature breadth."},
        "competitor": {"name": "PayRival", "note": "ops runs PayRival for case management but it can't reconcile across processors, so analysts stitch reports by hand."},
        "deal": {"acv": "$420k", "floor": "12%", "champion": "Head of Payment Ops", "eb": "engaged (CFO)",
                 "stage": "Negotiation", "score": 86, "win_probability": "72%", "days_in_stage": 26,
                 "risk": "security review and PCI scope must clear before signature.",
                 "action": "complete the security questionnaire and confirm PCI scope with their CISO.",
                 "pricing_note": "CFO wants a multi-year rate in exchange for volume commit"},
        "call": {"summary": "strong fit on reconciliation; security and PCI review is the gating item.",
                 "signals": "CFO engaged on the call; clear reconciliation pain and growth pressure.",
                 "risk_detail": "buyer shared transaction volumes, the PayRival contract value and named the CFO's target rate.",
                 "action": "fast-track the security questionnaire and propose a multi-year rate."},
        "lead": {"band": "hot", "stage": "SQL", "score": 90, "source": "Webinar: Fraud-Ops Automation", "why": "requested a security questionnaire and pricing",
                 "next": "send the security questionnaire and book a pricing review."},
        "transcript": (
            "AE (Maria Lopez): Where is the fraud-ops review focused?\n"
            "Champion (Tomas Berg, Head of Payment Ops): Reconciliation. Analysts spend two days a week stitching reports across processors.\n"
            "AE: And disputes?\n"
            "Champion: Resolution time is creeping up as volume grows. PayRival does case management but can't reconcile across processors.\n"
            "Economic Buyer (Lena Cho, CFO): I'll fund this if you can show the hours back and a multi-year rate. Our target is aggressive.\n"
            "AE: Understood. The gate is your security review and PCI scope — can we start the questionnaire now?\n"
            "Champion: Yes, I'll connect you with our CISO this week."
        ),
    },
    {
        "name": "Cedar Health", "slug": "cedar-health", "owner": "demo-ivan-ae", "team": "sales-west",
        "industry": "Healthcare services", "icp": "high",
        "summary": "Cedar Health runs outpatient clinics and care-operations teams. This broad card is the sanitized summary every employee may see.",
        "public_angle": "HIPAA-sensitive buyer — lead with clinician-hours ROI; PHI and commercial detail in the sales-owner view.",
        "signal": {"title": "Cedar Health Patient-Throughput Program", "phrase": "patient-throughput improvement program",
                   "slug": "throughput-program",
                   "sentence": "Cedar Health launched a patient-throughput improvement program and wants to free clinician time spent on manual reporting."},
        "roi": {"proof": "a similar care-ops team freed 13 clinician-hours per week from manual reporting and improved throughput within a quarter.",
                "pain": "Clinician admin overload", "lesson": "measure value in clinician-hours returned to patient care."},
        "competitor": {"name": "MedSys", "note": "clinics use MedSys for records, but care-ops exports to spreadsheets for reporting, eating clinician time."},
        "deal": {"acv": "$360k", "floor": "14%", "champion": "Director of Clinical Ops", "eb": "not yet engaged",
                 "stage": "Proposal", "score": 69, "win_probability": "48%", "days_in_stage": 18,
                 "risk": "HIPAA/PHI handling review pending; economic buyer (COO) not yet engaged.",
                 "action": "deliver the HIPAA-readiness brief and request a COO introduction.",
                 "pricing_note": "buyer needs board-level ROI justification"},
        "call": {"summary": "clear clinician-time pain; HIPAA review and COO sponsorship are the open items.",
                 "signals": "Champion quantified clinician hours lost; throughput is a board priority.",
                 "risk_detail": "champion referenced patient-volume figures and that PHI handling must pass their compliance officer.",
                 "action": "send the HIPAA-readiness brief and a clinician-hours ROI model."},
        "lead": {"band": "warm", "stage": "SQL", "score": 67, "source": "Webinar: Care-Ops ROI", "why": "downloaded the HIPAA-readiness brief",
                 "next": "share the clinician-hours ROI model and request a COO intro."},
        "transcript": (
            "AE (Ivan Petrov): What's the throughput program trying to fix?\n"
            "Champion (Dr. Amara Singh, Director of Clinical Ops): Clinicians lose hours to manual reporting that should go to patients.\n"
            "AE: Roughly how many hours?\n"
            "Champion: Easily a dozen per clinician each week. MedSys holds the records but we export to spreadsheets for reporting.\n"
            "AE: Any constraints we should plan for?\n"
            "Champion: PHI handling must pass our compliance officer, and the COO signs off on spend at this level.\n"
            "AE: We'll bring the HIPAA-readiness brief and a clinician-hours ROI model for the COO."
        ),
    },
    {
        # Renewal-at-risk story: existing customer, engagement dropped, the champion
        # left the company, a competitor is courting the account — the save-the-renewal play.
        "name": "Solara Hospitality", "slug": "solara-hospitality", "owner": "demo-maria-ae", "team": "sales-east",
        "industry": "Hotels & hospitality", "icp": "high",
        "summary": "Solara Hospitality operates a boutique hotel group and is an existing customer up for renewal. This broad card is the sanitized summary every employee may see.",
        "public_angle": "Existing customer in a renewal window — lead with re-proving value to the new stakeholder; renewal specifics in the sales-owner view.",
        "signal": {"title": "Solara Hospitality Leadership Change", "phrase": "leadership change at the account",
                   "slug": "leadership-change",
                   "sentence": "Solara Hospitality's Director of Guest Operations — the internal champion for the platform — left the company, and product usage has dropped since the departure."},
        "roi": {"proof": "a similar guest-operations team cut nightly manual reporting by 10 hours per week and lifted guest-review response rates within 45 days.",
                "pain": "Manual reporting overhead", "lesson": "a saved renewal starts with re-proving value to the new stakeholder, not with a discount."},
        "competitor": {"name": "StayCentric", "note": "StayCentric is actively courting the account since the champion departed; their reps have been in front of the GM repeatedly during the renewal window."},
        "deal": {"acv": "$220k", "floor": "16%", "champion": "Director of Guest Operations (departed)",
                 "eb": "incoming Director of Guest Operations (not yet engaged)",
                 "stage": "Negotiation", "score": 52, "win_probability": "25%", "days_in_stage": 33,
                 "risk": "champion left the company; usage down since the departure; renewal window closes in about 45 days with StayCentric courting the account.",
                 "action": "multi-thread to the incoming Director of Guest Operations and book an executive business review before the renewal date.",
                 "pricing_note": "renewal quote held flat; buyer hinting at a competitive re-bid"},
        "call": {"summary": "usage down since the champion left; renewal at risk — multi-thread to the new stakeholder now.",
                 "signals": "Interim contact confirmed the renewal timeline; open to an executive business review.",
                 "risk_detail": "interim contact said nobody owns the dashboards since the champion left and that a competitor is pressing the GM during the renewal window.",
                 "action": "book the executive business review and rebuild the value story for the incoming director."},
        "lead": {"band": "warm", "stage": "SQL", "score": 61, "source": "Product usage alert: engagement drop",
                 "why": "weekly active usage fell sharply after the champion left the company",
                 "next": "re-engage the incoming Director of Guest Operations with an executive business review invite."},
        "transcript": (
            "AE (Maria Lopez): Thanks for making time. How is the team holding up through the transition?\n"
            "Interim Contact (Jonah Fields, Guest Operations Manager): Honestly, since our Director of Guest Operations left, nobody owns the dashboards. Usage dropped a lot.\n"
            "AE: What would make the renewal an easy yes for the new leadership?\n"
            "Interim Contact: Show the new director value fast. StayCentric has been calling our GM weekly — keep that between us.\n"
            "AE: Understood. Can we book an executive business review before the renewal date?\n"
            "Interim Contact: Yes, aim for the next 45 days or it gets hard."
        ),
    },
    {
        # Closed-won-pilot expansion story: quantified pilot result, reference-able
        # customer, open multi-site expansion deal — marketing proof + upsell.
        "name": "Ironclad Freight", "slug": "ironclad-freight", "owner": "demo-maria-ae", "team": "sales-east",
        "industry": "Logistics & supply chain", "icp": "high",
        "summary": "Ironclad Freight runs regional freight and warehousing operations. The pilot closed won with measured results; this broad card is the sanitized summary every employee may see.",
        "public_angle": "Reference customer — the pilot delivered quantified results and the customer agreed to reference calls; expansion economics in the sales-owner view.",
        "signal": {"title": "Ironclad Freight Network Expansion", "phrase": "distribution-network expansion",
                   "slug": "network-expansion",
                   "sentence": "Ironclad Freight announced three new regional distribution centers and wants the pilot results replicated across the expanded network."},
        "roi": {"proof": "the Ironclad pilot cut dock-to-stock time by 22% and saved 12 analyst-hours per week in the first 60 days; the customer agreed to be a public reference.",
                "pain": "Manual reporting overhead", "lesson": "a quantified pilot plus a willing reference is the fastest path to a multi-site expansion."},
        "competitor": {"name": "FreightMetric", "note": "FreightMetric monitors the legacy sites, but ops says it never produced a finance-verified savings number — our pilot result is the wedge for the expansion."},
        "deal": {"acv": "$340k", "floor": "15%", "champion": "VP Supply Chain Operations", "eb": "engaged (COO)",
                 "stage": "Proposal", "score": 83, "win_probability": "65%", "days_in_stage": 12,
                 "risk": "multi-site expansion rollout needs per-site change management; procurement wants the pilot savings re-validated by finance.",
                 "action": "send the finance-validated pilot ROI summary and lock the three-site expansion rollout plan.",
                 "pricing_note": "expansion priced on the pilot rate; COO expects a volume rate for all sites"},
        "call": {"summary": "pilot closed won with measured results; COO asked for the multi-site expansion proposal.",
                 "signals": "Pilot hit its 60-day success criteria; customer agreed to reference calls; COO on the call.",
                 "risk_detail": "buyer shared the internal budget ceiling for the expansion and the FreightMetric contract timing.",
                 "action": "deliver the three-site expansion proposal with the pilot ROI summary attached."},
        "lead": {"band": "hot", "stage": "SQL", "score": 84, "source": "Customer: pilot review meeting",
                 "why": "pilot hit its 60-day success criteria and the COO asked for an expansion proposal",
                 "next": "deliver the multi-site expansion proposal with the pilot ROI summary."},
        "transcript": (
            "AE (Maria Lopez): The pilot wrapped last week — how did the numbers land?\n"
            "Champion (Ravi Kapoor, VP Supply Chain Operations): Dock-to-stock time is down 22% and we're saving about 12 analyst-hours a week. Finance verified it.\n"
            "AE: Would you be open to being a reference?\n"
            "Champion: Yes — happy to take reference calls once the expansion is signed.\n"
            "Economic Buyer (Elaine Moss, COO): I want this at all three new distribution centers. Between us, I have budget approved up to $400k — don't quote me on that.\n"
            "AE: We'll bring a three-site expansion proposal priced on the pilot rate.\n"
            "Champion: Send it this month and we can sign before the quarter ends."
        ),
    },
]

# Derived list for shared event/campaign cards: (name, slug, owner, team, has_pd).
PERMISSIONED_COMPANIES = [(p["name"], p["slug"], p["owner"], p["team"], True) for p in PERMISSIONED_PROFILES]


# A deliberately denser account for the Workbench demo. It does not increase
# the GraphView response ceiling: it fills the existing one-hop budget exactly
# (company + 11 related cards) with a realistic cross-functional account story.
DENSE_GRAPH_DEMO = {
    "name": "Summit Grid Logistics",
    "slug": "summit-grid-logistics",
    "owner": "demo-ivan-ae",
    "team": "sales-west",
    "industry": "Logistics technology",
    "summary": "Summit Grid Logistics is a synthetic expansion account used to demonstrate a denser, cross-functional knowledge graph.",
    "signal_title": "Summit Grid Network Modernization",
}


def perm_dense_graph_card(card_type: str, entity_id: str, title: str, *,
                          name: str, slug: str, boundary: str = "broad",
                          access: str = "internal", owner: str = "",
                          team: str = "", detail: str = "") -> str:
    """Create one safe, related record for the dense Workbench demo account.

    The cards deliberately use real supported GraphView types and the same
    `company` relation the production projector reads. This keeps the dense
    visual scenario an integration fixture rather than a hand-drawn response.
    """
    extra = [f"company: demo-company-{slug}"]
    if owner:
        extra.append(f"owner: {owner}")
    if team:
        extra.append(f"team: {team}")
    fm = perm_frontmatter(card_type, entity_id, boundary, access, extra, [card_type, "demo"])
    type_specific = ""
    if card_type == "lead":
        type_specific = """
## Scoring

- Score: 82
- Score band: hot
- Funnel stage: SQL
- Contact: restricted://personal-data/demo-summit-grid-lead-contact
"""
    elif card_type == "call":
        type_specific = """
## Executive Summary

- Sanitized takeaway: the planning call confirmed the reporting pain and a dated decision window.
- Raw transcript: restricted://personal-data/demo-summit-grid-planning
"""
    body = f"""
# {title}

## Controlled Profile

- Company: [[Company - {name}]]

## Live Intelligence

{detail}

{type_specific}

## Linked Entities

- Company: [[Company - {name}]]

{common_sections("permissioned dense-graph demo generator")}"""
    return fm + "\n" + body

# Top-of-funnel prospects: broad-only accounts with a lead + signal but NO deal —
# the marketing side of the funnel (MQL / nurture / cold), so the demo spans
# MQL -> SQL -> deal without contradiction (these never show a linked deal).
PERMISSIONED_PROSPECTS = [
    {
        "name": "Vertex Logistics", "slug": "vertex-logistics", "industry": "Logistics & freight", "icp": "high",
        "summary": "Vertex Logistics is a synthetic top-of-funnel prospect. Marketing-generated, not yet sales-qualified.",
        "band": "hot", "score": 79, "stage": "MQL",
        "source": "Webinar: Freight ROI", "why": "downloaded the ROI calculator and visited pricing twice this week",
        "next": "route to sales for qualification — looks ready to promote to SQL.",
        "signal": {"title": "Vertex Logistics Carrier-Cost Review", "phrase": "carrier-cost reduction review",
                   "slug": "carrier-cost-review",
                   "sentence": "Vertex Logistics opened a carrier-cost reduction review and is benchmarking time-to-value before committing budget."},
    },
    {
        "name": "Lumen Retail", "slug": "lumen-retail", "industry": "Retail operations", "icp": "medium",
        "summary": "Lumen Retail is a synthetic mid-funnel prospect. Engaged with content, still being nurtured.",
        "band": "warm", "score": 58, "stage": "MQL",
        "source": "Content: Store-Ops guide", "why": "opened two nurture emails and attended one webinar",
        "next": "continue nurture; send the store-ops time-savings study.",
        "signal": {"title": "Lumen Retail Store-Ops Efficiency Push", "phrase": "store-ops efficiency push",
                   "slug": "store-ops-push",
                   "sentence": "Lumen Retail kicked off a store-ops efficiency push to cut manual reporting across locations."},
    },
    {
        "name": "Orchard Bank", "slug": "orchard-bank", "industry": "Retail banking", "icp": "medium",
        "summary": "Orchard Bank is a synthetic cold prospect. Early research only, low recent activity.",
        "band": "cold", "score": 38, "stage": "nurture",
        "source": "Content: whitepaper download", "why": "one whitepaper download three weeks ago, no activity since",
        "next": "keep on the quarterly nurture track until a fresh signal appears.",
        "signal": {"title": "Orchard Bank Back-Office Modernization", "phrase": "back-office modernization research",
                   "slug": "back-office-research",
                   "sentence": "Orchard Bank is in early research on back-office modernization with no defined timeline yet."},
    },
    {
        # Switched-vendor intent prospect: public dissatisfaction with a competitor
        # (G2 review + RFP hint) — the intent signal marketing loves. No deal yet.
        "name": "Cinder Analytics", "slug": "cinder-analytics", "industry": "Data analytics software", "icp": "high",
        "summary": "Cinder Analytics is a synthetic top-of-funnel prospect showing switched-vendor intent. Marketing-generated, not yet sales-qualified.",
        "band": "hot", "score": 76, "stage": "MQL",
        "source": "Intent: public G2 review + RFP hint",
        "why": "publicly criticized its current analytics vendor in a G2 review and hinted at an RFP for a replacement",
        "next": "fast-track to sales with the vendor-switch migration checklist.",
        "signal": {"title": "Cinder Analytics Vendor-Switch Intent", "phrase": "switched-vendor intent",
                   "slug": "vendor-switch-intent",
                   "sentence": "Cinder Analytics posted a public G2 review criticizing its current analytics vendor's reporting and signaled an upcoming RFP for a replacement platform."},
    },
]


# Synthetic Google Drive connector manifest written into the permissioned demo
# vault. No OAuth or network: the bridge reads this file to demo a governed
# ingest flow (list folder -> propose -> review -> apply). `boundary` gates each
# folder per role exactly like card boundaries, so listing is no-leak. `maps_to`
# is the entity_id a processed file would feed; `status` drives the new/processed
# answer. Regenerate or delete freely with the rest of the demo.
GDRIVE_MANIFEST: dict = {
    "connector": "google-drive",
    "synthetic": True,
    "account": "demo-curator@saleswiki.local",
    "folders": {
        "Sales/Q3-Calls": {
            "boundary": "sales-confidential",
            "files": [
                {"id": "gd-001", "name": "Atlas Foods — Discovery 2026-05-29.txt",
                 "kind": "call-transcript", "status": "new", "maps_to": "demo-company-atlas-foods"},
                {"id": "gd-002", "name": "BluePeak — Pricing follow-up.eml",
                 "kind": "email", "status": "new", "maps_to": "demo-company-bluepeak-energy"},
                {"id": "gd-003", "name": "Northstar — signed NDA.pdf",
                 "kind": "document", "status": "processed", "maps_to": "demo-company-northstar-robotics"},
            ],
        },
        "Marketing/Webinars": {
            "boundary": "broad",
            "files": [
                {"id": "gd-010", "name": "Q3 ROI Webinar — registrants.csv",
                 "kind": "lead-list", "status": "new", "maps_to": "demo-campaign-q3-roi-push"},
            ],
        },
    },
}


def generate_permissioned_demo(perm_root: Path) -> None:
    """Generate the isolated permissioned demo sub-vault with real folder boundaries.

    Layout: <perm_root>/{broad,sales-confidential,personal-data}/... All cards are
    synthetic and demo-scoped. A non-Markdown note documents the boundary layout.
    """
    perm_root.mkdir(parents=True, exist_ok=True)
    write(perm_root / "README.txt", (
        "SalesWiki permissioned demo sub-vault (synthetic).\n"
        "Folders are physical permission boundaries: broad, sales-confidential, personal-data.\n"
        "Mapped to boundaries by schemas/boundary-registry.json. Regenerate or delete freely.\n"
    ))
    for p in PERMISSIONED_PROFILES:
        name, slug, owner, team = p["name"], p["slug"], p["owner"], p["team"]
        comp = p["competitor"]["name"]
        comp_file = f"Competitor Intel - {name} - {comp}.md"
        signal_title = p["signal"]["title"]
        # broad
        write(perm_root / "broad" / "wiki" / "entities" / "companies" / f"Company - {name}.md",
              perm_company_broad(name, slug, industry=p["industry"], icp=p["icp"], summary=p["summary"],
                                 public_angle=p["public_angle"], signal_title=signal_title))
        write(perm_root / "broad" / "wiki" / "entities" / "leads" / f"Lead - {name}.md",
              perm_lead_broad(name, slug, p["lead"]["band"], p["lead"]["source"], p["lead"]["why"],
                              score=p["lead"]["score"], stage=p["lead"]["stage"], next_action=p["lead"]["next"]))
        write(perm_root / "broad" / "wiki" / "entities" / "sources" / f"Source - {signal_title}.md",
              perm_market_signal_broad(name, slug, signal_title=signal_title, signal_phrase=p["signal"]["phrase"],
                                       signal_sentence=p["signal"]["sentence"], signal_slug=p["signal"]["slug"]))
        write(perm_root / "broad" / "wiki" / "entities" / "private-cases" / f"Private Case - {name} - Sanitized ROI Proof.md",
              perm_private_case_broad(name, slug, roi_proof=p["roi"]["proof"], roi_pain=p["roi"]["pain"], lesson=p["roi"]["lesson"]))
        # sales-confidential
        write(perm_root / "sales-confidential" / "wiki" / "entities" / "deals" / f"Deal - {name} - Pilot.md",
              perm_deal_salesconf(name, slug, owner, team, **p["deal"]))
        write(perm_root / "sales-confidential" / "wiki" / "entities" / "calls" / f"Call - {name} - Discovery.md",
              perm_call_salesconf(name, slug, owner, team, **p["call"]))
        write(perm_root / "sales-confidential" / "wiki" / "entities" / "competitor-intel" / comp_file,
              perm_competitor_intel_salesconf(name, slug, owner, team, competitor=comp, comp_note=p["competitor"]["note"]))
        # personal-data (handle + sanitized extract; the raw transcript is
        # generator input only and never lands in a card body)
        write(perm_root / "personal-data" / "refs" / f"Personal-Data Ref - {name}.md",
              perm_personaldata_ref(name, slug, transcript=p["transcript"]))

    # Dense account: exactly eleven related, role-authorized cards. The set
    # spans every current Workbench sector, so the client is exercised against
    # a genuine MCP projection instead of an oversized visual mock.
    dense = DENSE_GRAPH_DEMO
    name, slug, owner, team = dense["name"], dense["slug"], dense["owner"], dense["team"]
    write(perm_root / "broad" / "wiki" / "entities" / "companies" / f"Company - {name}.md",
          perm_company_broad(name, slug, industry=dense["industry"], icp="high", summary=dense["summary"],
                             public_angle="Expansion account — coordinate commercial, adoption and evidence signals in one account plan.",
                             signal_title=dense["signal_title"]))
    dense_cards = [
        ("broad", "people", "person", "demo-person-summit-grid-champion", "Person - Summit Grid Operations Champion", "The operations champion is coordinating the evaluation across network teams."),
        ("broad", "leads", "lead", "demo-lead-summit-grid-logistics", "Lead - Summit Grid Logistics", "Recent expansion intent and repeated ROI-calculator activity make this an active SQL."),
        ("sales-confidential", "deals", "deal", "demo-deal-summit-grid-expansion", "Deal - Summit Grid Logistics - Expansion", "The expansion is in proposal review; protect scope while confirming the executive sponsor."),
        ("sales-confidential", "calls", "call", "demo-call-summit-grid-planning", "Call - Summit Grid Logistics - Planning", "The planning call confirmed warehouse reporting effort and a dated decision window."),
        ("sales-confidential", "competitor-intel", "competitor-intel", "demo-competitor-summit-grid-routeflow", "Competitor Intel - Summit Grid Logistics - RouteFlow", "RouteFlow is the incumbent; keep replacement strategy within the account team."),
        ("broad", "sources", "source", "demo-source-summit-grid-modernization", f"Source - {dense['signal_title']}", "A public modernization initiative makes time-to-value the strongest outreach angle."),
        ("broad", "events", "event", "demo-event-summit-grid-operations-forum", "Event - Summit Grid Operations Forum", "The account is attending an operations forum where the team can validate the expansion narrative."),
        ("broad", "campaigns", "campaign", "demo-campaign-summit-grid-roi", "Campaign - Summit Grid ROI Sequence", "A short ROI proof sequence supports the account team's executive follow-up."),
        ("broad", "pain-points", "pain-point", "demo-pain-summit-grid-network-reporting", "Pain Point - Summit Grid Network Reporting", "Network teams still reconcile reporting manually across warehouses."),
        ("broad", "private-cases", "private-case", "demo-private-case-summit-grid-proof", "Private Case - Summit Grid Logistics - Sanitized Proof", "A comparable team shortened weekly reporting effort without exposing customer-sensitive detail."),
        ("sales-confidential", "tasks", "task", "demo-task-summit-grid-exec-review", "Task - Summit Grid Executive Review", "Prepare the executive review with the ROI model, pilot scope and open sponsor question."),
    ]
    for boundary, folder, card_type, entity_id, title, detail in dense_cards:
        is_sales = boundary == "sales-confidential"
        write(perm_root / boundary / "wiki" / "entities" / folder / f"{title}.md",
              perm_dense_graph_card(card_type, entity_id, title, name=name, slug=slug, boundary=boundary,
                                    access="sales-confidential" if is_sales else "internal",
                                    owner=owner if is_sales else "", team=team if is_sales else "", detail=detail))
    write(perm_root / "broad" / "wiki" / "entities" / "events" / "Event - Sales Tech Summit 2026.md", perm_event_broad(PERMISSIONED_COMPANIES))
    write(perm_root / "broad" / "wiki" / "entities" / "campaigns" / "Campaign - Q3 ROI Push.md", perm_campaign_broad(PERMISSIONED_COMPANIES))
    for slug, (title, angle, asset) in PERMISSIONED_PAINS.items():
        write(perm_root / "broad" / "wiki" / "entities" / "pain-points" / f"Pain Point - {title}.md", perm_painpoint_broad(title, slug, angle, asset))
    # Top-of-funnel prospects: MQL/nurture/cold leads with NO deal yet — marketing's
    # side of the funnel, distinct from the 7 sales-qualified accounts above.
    for pr in PERMISSIONED_PROSPECTS:
        name, slug = pr["name"], pr["slug"]
        sig = pr["signal"]
        write(perm_root / "broad" / "wiki" / "entities" / "companies" / f"Company - {name}.md",
              perm_company_broad(name, slug, industry=pr["industry"], icp=pr["icp"], summary=pr["summary"],
                                 public_angle="Top-of-funnel prospect — no active deal yet.",
                                 signal_title=sig["title"], has_deal=False, status="prospect"))
        write(perm_root / "broad" / "wiki" / "entities" / "sources" / f"Source - {sig['title']}.md",
              perm_market_signal_broad(name, slug, signal_title=sig["title"], signal_phrase=sig["phrase"],
                                       signal_sentence=sig["sentence"], signal_slug=sig["slug"]))
        write(perm_root / "broad" / "wiki" / "entities" / "leads" / f"Lead - {name}.md",
              perm_lead_broad(name, slug, pr["band"], pr["source"], pr["why"],
                              score=pr["score"], stage=pr["stage"], next_action=pr["next"]))
    # Synthetic Google Drive connector manifest (no OAuth/network) for the demo's
    # governed ingest flow. Lives outside the boundary folders, under connectors/.
    manifest_path = perm_root / "connectors" / "gdrive-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(GDRIVE_MANIFEST, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    # Append-only synthetic observations power the dashboard read-model demo.
    # They are not forecasts and contain neither personal data nor CRM values.
    # A real pilot must write equivalent reviewed observations outside this repo.
    score_paths = {
        "bluepeak-energy": [61, 65, 69, 74],
        "northstar-robotics": [72, 77, 81, 84],
        "atlas-foods": [83, 82, 80, 79],
        "meridian-payments": [77, 80, 83, 86],
        "cedar-health": [63, 65, 67, 69],
        "solara-hospitality": [73, 68, 62, 56],
        "ironclad-freight": [70, 75, 81, 87],
        "summit-grid-logistics": [75, 78, 80, 82],
    }
    rows = []
    for slug, scores in score_paths.items():
        for offset, score in enumerate(scores):
            rows.append(json.dumps({
                "company_id": f"demo-company-{slug}",
                "observed_on": day(-21 + offset * 7),
                "score": score,
                "synthetic": True,
                "source": "demo-dashboard-baseline",
            }, ensure_ascii=False, separators=(",", ":")))
    observations_path = perm_root / "state" / "dashboard-observations.jsonl"
    observations_path.parent.mkdir(parents=True, exist_ok=True)
    observations_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def generate(output_root: Path, reset: bool) -> None:
    if reset:
        safe_reset(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    write(output_root / "README.md", """# SalesWiki Demo Vault

This vault is synthetic demo data only.

- Every generated card uses `dataset: demo`.
- Every generated card uses `synthetic: true`.
- Demo data can be regenerated or deleted without approval.
- Do not use demo cards for CRM, real reporting or customer-facing claims.
""")

    for dashboard in (PROJECT_ROOT / "dashboards").glob("*.base"):
        dst = output_root / "dashboards" / dashboard.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dashboard, dst)

    companies = [
        ("Orion Foods", "orion-foods", "alex-demo", "target", "food manufacturing", "high"),
        ("Atlas Robotics", "atlas-robotics", "maria-demo", "prospect", "industrial robotics", "high"),
        ("Nimbus Health", "nimbus-health", "alex-demo", "watchlist", "health services", "medium"),
        ("Vector Finance", "vector-finance", "maria-demo", "target", "financial services", "medium"),
        ("Helio Retail", "helio-retail", "alex-demo", "prospect", "retail operations", "high"),
    ]
    for company, slug, owner, status, segment, priority in companies:
        write(output_root / "wiki" / "entities" / "companies" / f"Company - {company}.md", company_card(company, slug, owner, status, segment, priority))
        write(output_root / "wiki" / "entities" / "people" / f"Person - {company} Buyer.md", person_card(f"{company} Buyer", f"{slug}-buyer", company, slug, "VP Operations"))
        write(output_root / "raw" / "research" / f"{slug}.md", f"# Demo research note for {company}\n\nSynthetic source only.\n")

    lead_specs = [
        ("Orion Foods", "orion-foods", 1, "alex-demo", 91, "hot", "qualification-mql", day(2)),
        ("Orion Foods", "orion-foods", 2, "alex-demo", 76, "warm", "outside-pipeline", day(4)),
        ("Atlas Robotics", "atlas-robotics", 1, "maria-demo", 88, "hot", "sql", day(2)),
        ("Atlas Robotics", "atlas-robotics", 2, "maria-demo", 67, "nurture", "outside-pipeline", day(11)),
        ("Nimbus Health", "nimbus-health", 1, "alex-demo", 72, "warm", "qualification-mql", day(5)),
        ("Nimbus Health", "nimbus-health", 2, "alex-demo", 55, "nurture", "outside-pipeline", day(13)),
        ("Vector Finance", "vector-finance", 1, "maria-demo", 84, "warm", "qualification-mql", day(3)),
        ("Vector Finance", "vector-finance", 2, "maria-demo", 43, "low", "outside-pipeline", day(16)),
        ("Helio Retail", "helio-retail", 1, "alex-demo", 90, "hot", "sql", day(2)),
        ("Helio Retail", "helio-retail", 2, "alex-demo", 71, "warm", "outside-pipeline", day(7)),
    ]
    for args in lead_specs:
        company, _, idx, *_ = args
        write(output_root / "wiki" / "entities" / "leads" / f"Lead - {company} - Primary Buyer {idx}.md", lead_card(*args))

    for company, slug, owner, score, band, stage, close_date in [
        ("Orion Foods", "orion-foods", "alex-demo", 82, "warm", "Qualification", day(46)),
        ("Atlas Robotics", "atlas-robotics", "maria-demo", 89, "hot", "Proposal", day(32)),
    ]:
        write(output_root / "wiki" / "entities" / "deals" / f"Deal - {company} - Pilot.md", deal_card(company, slug, owner, score, band, stage, close_date))
        write(output_root / "wiki" / "entities" / "calls" / f"Call - {company} - 2026-05-29 - Discovery.md", call_card(company, slug, owner))
        write(output_root / "raw" / "calls" / f"{slug}-discovery.txt", f"Demo transcript for {company}. Synthetic only. Buyer asked for dashboard walkthrough and next-step clarity.\n")

    tasks = [
        ("Follow Up - Orion Foods", "follow-up-orion-foods", "Lead - Orion Foods - Primary Buyer 1", "alex-demo", day(2), "high"),
        ("Deal Next Step - Orion Foods", "deal-next-orion-foods", "Deal - Orion Foods - Pilot", "alex-demo", day(3), "high"),
        ("Follow Up - Atlas Robotics", "follow-up-atlas-robotics", "Lead - Atlas Robotics - Primary Buyer 1", "maria-demo", day(2), "high"),
        ("Review Marketing Insight - Operations Pain", "review-marketing-operations-pain", "Pain Point - Slow Handoff", "marketing-demo", day(5), "medium"),
        ("Clean Demo Low Confidence Items", "clean-demo-quality", "Topic - RevOps Workflow", "curator-demo", day(6), "medium"),
    ]
    for task in tasks:
        title = task[0]
        write(output_root / "wiki" / "entities" / "tasks" / f"Task - {title}.md", task_card(*task))

    for title, folder, content in [
        ("Topic - RevOps Workflow", *knowledge_card("topic", "topics", "Topic - RevOps Workflow", "demo-topic-revops-workflow", "active", "marketing-demo")),
        ("Pain Point - Slow Handoff", *knowledge_card("pain-point", "pain-points", "Pain Point - Slow Handoff", "demo-pain-slow-handoff", "active", "marketing-demo")),
        ("Objection - Too Much Manual Work", *knowledge_card("objection", "objections", "Objection - Too Much Manual Work", "demo-objection-manual-work", "active", "marketing-demo")),
        ("Use Case - Daily Sales Priority", *knowledge_card("use-case", "use-cases", "Use Case - Daily Sales Priority", "demo-use-case-daily-sales-priority", "active", "marketing-demo")),
    ]:
        write(output_root / "wiki" / "entities" / folder / f"{title}.md", content)

    write(output_root / "wiki" / "entities" / "campaigns" / "Campaign - Demo ABM Sprint.md", knowledge_card("campaign", "campaigns", "Campaign - Demo ABM Sprint", "demo-campaign-abm-sprint", "active", "marketing-demo")[1])
    write(output_root / "wiki" / "entities" / "content-briefs" / "Content Brief - SalesWiki Dashboard Story.md", knowledge_card("content-brief", "content-briefs", "Content Brief - SalesWiki Dashboard Story", "demo-content-brief-dashboard-story", "draft", "marketing-demo")[1])
    write(output_root / "wiki" / "entities" / "private-cases" / "Private Case - Demo Sanitized Implementation.md", knowledge_card("private-case", "private-cases", "Private Case - Demo Sanitized Implementation", "demo-private-case-sanitized-implementation", "draft", "marketing-demo")[1])

    for title, slug in [
        ("Demo Market Signal - Sales Knowledge", "market-signal-sales-knowledge"),
        ("Demo News - Operations Automation", "news-operations-automation"),
        ("Demo Research - Dashboard Adoption", "research-dashboard-adoption"),
    ]:
        write(output_root / "wiki" / "entities" / "sources" / f"Source - {title}.md", source_card(title, slug))
        write(output_root / "raw" / "research" / f"{slug}.md", f"# {title}\n\nSynthetic demo source only.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate isolated SalesWiki demo vault data.")
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "demo" / "demo-vault"), help="Demo vault root.")
    parser.add_argument("--reset", action="store_true", help="Delete existing demo vault first. Only allowed under demo/.")
    parser.add_argument("--permissioned-root", default=str(PROJECT_ROOT / "demo" / "permissioned"), help="Permissioned demo sub-vault root.")
    parser.add_argument("--skip-permissioned", action="store_true", help="Do not generate the permissioned demo sub-vault.")
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    generate(output_root, args.reset)
    print(f"Generated demo vault: {output_root}")

    if not args.skip_permissioned:
        perm_root = Path(args.permissioned_root).resolve()
        if args.reset:
            safe_reset(perm_root)
        generate_permissioned_demo(perm_root)
        print(f"Generated permissioned demo: {perm_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
