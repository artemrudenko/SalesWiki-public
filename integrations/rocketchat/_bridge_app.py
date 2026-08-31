"""Command routing and polling loop for the optional Rocket.Chat demo bridge."""
from __future__ import annotations

import os
import re
import sys
import threading
import time

from integrations.chat.runtime import ChatRuntime

from _bridge_client import RocketChat
from _bridge_common import *  # noqa: F403
from _bridge_transport import RocketChatTransport
from _bridge_wiki import Wiki
from saleswiki_runtime.config import ConfigError, load_runtime_settings

def roles_help() -> str:
    lines = ["🤖 **SalesWiki** · available roles (`role: <name>`):", ""]
    for name, (_actor, desc) in ROLES.items():
        lines.append(f"- `{name}` — {desc}")
    lines += [
        "",
        "Switch role: `role: account-exec`. Ask: `? company brief BluePeak Energy`.",
        "If you have no access — I'll tell you to ask an admin to elevate your access.",
        "Request access to a closed source: `request access <reason>`.",
        "Request queue (for curator/admin): `review queue`.",
        "Decide on a request (curator/admin): `approve <id> [days]` / `reject <id> <reason>`.",
        "Approval actually grants access (30 days by default); revoke — `revoke <id> <reason>`.",
        "When a request is filed, approvers get a notification; on entering a reviewer role — a pending counter.",
        "Behind the glass: the full card by zone — `card <company>`; how it all works — `how it works`.",
        "Data sources: `drive` (connected folders) → `drive <folder>` → `process <id>` (governed ingest).",
        "Full cheat-sheet with all examples — command `demo`.",
    ]
    return "\n".join(lines)


def _cheat_table(headers: list[str], rows: list[list[str]]) -> str:
    """Aligned monospace table in a code fence (renders consistently in Rocket.Chat)."""
    table = [headers] + rows
    widths = [max(len(r[c]) for r in table) for c in range(len(headers))]
    def fmt(r: list[str]) -> str:
        return "  ".join(r[c].ljust(widths[c]) for c in range(len(headers))).rstrip()
    lines = [fmt(headers), "  ".join("-" * w for w in widths)]
    lines += [fmt(r) for r in rows]
    return "```\n" + "\n".join(lines) + "\n```"


# Per-role demo walkthroughs (`демо <роль>`): a 4-beat story per role — who they
# are, what they can do, what is 🔒 (and why), and the governance they can drive.
# Commands here must match real bridge behaviour (kept in sync with the catalogue).
ROLE_DEMOS: dict[str, dict] = {
    "employee": {
        "who": "A regular employee: general public cards, no commercial secrets.",
        "can": [
            ["? company brief BluePeak Energy", "signal + sanitized ROI, no pricing"],
            ["? lead priority BluePeak Energy", "lead with a numeric score and \"why now\""],
            ["? content ideas", "pains → angle → asset"],
            ["? my day", "today's tasks per the role's access"],
        ],
        "cannot": [
            ["? deal risk BluePeak Energy", "🔒 deal details — sales roles only"],
            ["pricing / competitor in the brief", "🔒 stored in sales-confidential"],
        ],
        "gov": [
            ["request access <reason>", "access request → goes to a curator"],
            ["flag stale <note>", "flag \"data is wrong/stale\""],
            ["request redaction <reason>", "review/hide personal data"],
        ],
        "note": "A request filed here is later handled by `demo curator`.",
    },
    "sales-rep": {
        "who": "Sales Rep (SDR): a seller's general access, but no deal risk and no private deal details.",
        "can": [
            ["? company brief BluePeak Energy", "public company card"],
            ["? lead priority BluePeak Energy", "lead + numeric score"],
            ["? my day", "today's tasks"],
        ],
        "cannot": [
            ["? deal risk BluePeak Energy", "🔒 deal risk is not for SDR"],
            ["pricing / competitor", "🔒 sales-confidential"],
        ],
        "gov": [["request access <reason>", "access request"],
                ["flag stale <note>", "flag a data error"]],
        "note": "Access is almost like employee, but this is a selling role.",
    },
    "account-exec": {
        "who": "Account Executive: account owner — commercial details on THEIR OWN deals.",
        "can": [
            ["? company brief BluePeak Energy", "full: + competitor (RivalCorp) + pricing"],
            ["? deal risk BluePeak Energy", "Score · Win % · Value + risk (own deal)"],
            ["? call prep BluePeak Energy", "sanitized prep + handle to the transcript"],
            ["? lead priority BluePeak Energy", "lead + linked deal risk"],
        ],
        "cannot": [
            ["? deal risk Northstar Robotics", "🔒 other team (ABAC, sales-east)"],
            ["raw call transcript", "🔒 personal-data — only admin/by grant"],
        ],
        "gov": [["flag stale <note>", "flag an error"],
                ["request redaction <reason>", "personal-data review"]],
        "note": "Contrast: what was 🔒 for employee is open for AE — say it out loud.",
    },
    "head-of-sales": {
        "who": "Head of Sales: the whole team — pipeline and risks in full.",
        "can": [
            ["? pipeline", "DASHBOARD: Open deals · Total · Weighted · by stage"],
            ["? deal risk all", "all the team's deals at once"],
            ["? deal risk Northstar Robotics", "sees another team (above team level)"],
            ["? my day", "team summary"],
        ],
        "cannot": [["raw transcript (personal-data)", "🔒 only admin/by grant"]],
        "gov": [["review queue", "incoming requests"],
                ["approve <id> [days]", "approve (HoS — an approver)"],
                ["apply", "run the worker → edit into Review Needed"]],
        "note": "The same `? pipeline` arrives WITHOUT figures for marketing — the next contrast.",
    },
    "revenue-ops": {
        "who": "Revenue Ops: operational pipeline and risk data across the whole team.",
        "can": [
            ["? pipeline", "pipeline dashboard in figures"],
            ["? deal risk all", "cross-view of deals"],
            ["? deal risk BluePeak Energy", "details of any deal"],
        ],
        "cannot": [["raw transcript (personal-data)", "🔒 only admin/by grant"]],
        "gov": [["review queue", "incoming requests"],
                ["approve <id> [days]", "approve"], ["apply", "run the worker"]],
        "note": "Like HoS on pipeline data, from an operational angle.",
    },
    "marketing": {
        "who": "Marketing: market signals and content angles, no commercial secrets.",
        "can": [
            ["? campaign Q3 ROI Push", "campaign brief + target accounts"],
            ["? content ideas", "pains → angle → asset"],
            ["? lead priority all", "the whole funnel: own MQL/nurture (Vertex/Lumen/Orchard/Cinder) + SQL"],
            ["? company brief BluePeak Energy", "market signals + sanitized ROI as a content angle"],
        ],
        "cannot": [
            ["? deal risk BluePeak Energy", "🔒 commercial details — not for marketing"],
            ["? pipeline", "arrives WITHOUT figures (aggregate) — no-leak, not a bug"],
        ],
        "gov": [["flag stale <note>", "flag an error"],
                ["request redaction <reason>", "personal-data review"]],
        "note": "Twist: the same `? pipeline` that had figures for HoS is an empty aggregate for marketing.",
    },
    "legal": {
        "who": "Legal: personal-data review, no commercial secrets.",
        "can": [["? company brief BluePeak Energy", "public card"],
                ["? content ideas", "public materials"]],
        "cannot": [["? deal risk BluePeak Energy", "🔒 commercial secrets are not for legal"],
                   ["pricing", "🔒 sales-confidential"]],
        "gov": [["request redaction <reason>", "initiate a personal-data review"]],
        "note": "The role's focus is privacy, not commerce.",
    },
    "curator": {
        "who": "Knowledge Curator: governance — handles requests and applies edits.",
        "can": [
            ["review queue", "incoming proposals (access/flags/redaction)"],
            ["approve <id> [days]", "access → grant; flag/redaction → to the worker"],
            ["reject <id> <reason>", "reject the request"],
            ["apply", "run the single-writer worker → edit into Review Needed"],
            ["revoke <id> <reason>", "remove an issued grant"],
        ],
        "cannot": [["raw transcript (personal-data)", "🔒 reading personal data — for admin"]],
        "note": "Closes the loop: employee request → approve → apply → visible in the card.",
    },
    "admin": {
        "who": "Admin: full access to everything, including personal data.",
        "can": [
            ["? company brief BluePeak Energy", "everything, including personal-data"],
            ["? deal risk Northstar Robotics", "any deal, any team"],
            ["approve <id>", "including grants on personal-data"],
        ],
        "cannot": [],
        "note": "Capstone: shows what is hidden from the other roles — for comparison.",
    },
}

# Compact role-picker line shown under every demo view.
_ROLE_PICKER = ("_One role at a time: `demo employee` · `demo account-exec` · "
                "`demo head-of-sales` · `demo marketing` · `demo curator`. "
                "Full catalogue — `demo`._")


def _role_demo(role: str) -> str:
    """Render the focused `демо <роль>` walkthrough for one role."""
    d = ROLE_DEMOS.get(role)
    if d is None:
        return f"There is no separate scenario for role `{role}`. Full catalogue — `demo`."
    parts = [f"🎬 **demo · role `{role}`**", f"_{d['who']}_", "",
             "**✅ What they can do (step by step):**", _cheat_table(["Command", "What it shows"], d["can"])]
    if d.get("cannot"):
        parts += ["**🔒 What they CANNOT do (and why):**", _cheat_table(["Command", "Why hidden"], d["cannot"])]
    if d.get("gov"):
        parts += ["**🛠 Governance (what they can propose/decide):**",
                  _cheat_table(["Command", "What it does"], d["gov"])]
    if d.get("note"):
        parts.append(f"_{d['note']}_")
    parts.append(_ROLE_PICKER)
    return "\n".join(parts)


# The hands-free presenter script for `демо старт`: (narrator comment, command).
# A None command = narrator-only beat. `{pid}` is replaced with the last
# proposal id seen in a reply, so approve/revoke always target the right one.
AUTOPLAY_SCRIPT: list[tuple[str, "str | None"]] = [
    ("Autopilot demo — the same governed vault, driven beat by beat. "
     "Watch how ONE question changes with the role.", None),
    ("Beat 1 — role contrast. Marketing asks about the hero account first.", "роль: marketing"),
    ("Marketing sees the market signal and the sanitized ROI proof — no pricing, "
     "no competitor intel.", "? бриф по BluePeak Energy"),
    ("The account owner asks the exact same question…", "роль: account-exec"),
    ("…and pricing, the discount floor and RivalCorp appear. The role decides "
     "what gets extracted — before the answer is assembled.", "? бриф по BluePeak Energy"),
    ("Beat 2 — honesty. A company the vault does not know: no guessing, no "
     "silent substitution.", "? бриф по Acme Industrial"),
    ("Beat 3 — the stories sales lives in. Switch to the Head of Sales view.", "роль: head-of-sales"),
    ("Renewal at risk: the champion LEFT, ~45 days to renewal, a competitor is "
     "courting the account.", "? риск по сделке Solara Hospitality"),
    ("Closed-won proof: a pilot with measured results and a reference-able "
     "customer — marketing's case study, sales' expansion.", "? бриф по Ironclad Freight"),
    ("Intent lead: a public complaint about its current vendor + an RFP hint.", "? приоритет лида Cinder Analytics"),
    ("The whole pipeline rolled up: totals, weighted value, by stage.", "? пайплайн"),
    ("The same rollup as a picture — rendered from the identical role-gated "
     "data, so the chart can never show more than the role may read.", "график"),
    ("Beat 4 — the governed access loop. A viewer hits a locked answer…", "роль: employee"),
    ("Locked — but not a dead end.", "? риск по сделке BluePeak Energy"),
    ("…so they file a real, audited access request.", "запросить доступ need deal risk for BluePeak"),
    ("Approvers get a 🔔 the moment they arrive.", "роль: curator"),
    ("The curator reviews the queue…", "очередь ревью"),
    ("…and issues a scoped grant: 7 days, ONE company, no role switch.", "одобрить {pid} 7"),
    ("Back as the viewer:", "роль: employee"),
    ("The same question is now visible — the grant is live.", "? риск по сделке BluePeak Energy"),
    ("And it stays revocable:", "роль: curator"),
    ("Revoked — access disappears immediately.", "отозвать {pid} autopilot finished the beat"),
    ("Beat 5 — where data comes from. The AE opens the connected Drive.", "роль: account-exec"),
    ("Folders are role-gated; new files are flagged.", "драйв"),
    ("Processing a file does NOT write the card — it files an ingest proposal.", "обработать gd-001"),
    ("The same review loop picks it up.", "роль: curator"),
    ("Approve the ingest…", "одобрить {pid}"),
    ("…and the single-writer worker lands it in the card's Review Needed.", "применить"),
    ("Beat 6 — behind the glass: the full source-of-truth card the gateway "
     "filters per role.", "карточка BluePeak Energy"),
    ("And the mechanics: card birth, immutability, the funnel, the governance "
     "loop.", "как это работает"),
    ("That's the autopilot run: every answer cited, roles decide extraction, "
     "access checked BEFORE the answer is assembled. Try your own questions — "
     "or `демо` for the full catalogue.", None),
]


def run_autoplay(rc, room_id: str, wiki: "Wiki", state: dict, delay: float) -> None:
    """Post the presenter script into the channel hands-free: a 🎙️ narrator
    comment, the command "typed" with a ▶️ prefix (so the poll loop never
    re-processes it), then the bridge's own answer. `демо стоп` halts before
    the next beat. Runs on a background thread; the poll loop stays live."""
    # Work on a private copy of the channel state: the script switches roles
    # (ending as curator), and the live poll loop shares this dict — without the
    # copy an interjected user command would run under the script's role and the
    # channel would be left as curator after the show.
    state = dict(state)
    pid = "1"
    rc.post(room_id, f"▶️ **Autopilot started** — {len(AUTOPLAY_SCRIPT)} beats, "
                     f"~{int(delay)}s pause each. Stop any time: `демо стоп`.")
    for i, (comment, command) in enumerate(AUTOPLAY_SCRIPT, 1):
        if wiki.autoplay_stop.is_set():
            rc.post(room_id, "⏹ Autopilot stopped. The vault is yours — try `демо` for the catalogue.")
            return
        try:
            rc.post(room_id, f"🎙️ _{comment}_")
            if command:
                cmd = command.format(pid=pid)
                rc.post(room_id, f"▶️ `{cmd}`")
                reply = handle(cmd, state, wiki)
                if isinstance(reply, str) and reply:
                    found = re.findall(r"proposal-0*(\d+)", reply)
                    if found:
                        pid = found[-1]
                    rc.post(room_id, with_separator(reply))
                elif isinstance(reply, dict) and "upload" in reply:
                    art = reply["upload"]
                    rc.upload(room_id, art["filename"], art["content"],
                              art["ctype"], art.get("caption", ""))
        except Exception as exc:  # a broken beat must not kill the show
            rc.post(room_id, f"⚠️ Beat {i} failed ({exc}) — continuing.")
        time.sleep(delay)
    rc.post(room_id, "🏁 **Autopilot finished.** The vault is live — ask your own "
                     "questions or type `демо` for the full catalogue.")


def demo_help() -> str:
    """Full demo catalogue rendered as aligned tables: every scenario the demo can
    show, by direction, with the exact messages to type and what each proves."""
    parts = [
        "🎬 **SalesWiki demo — full catalogue of scenarios**",
        "_7 companies: BluePeak Energy (energy) · Atlas Foods (food) · Northstar Robotics "
        "(robotics) · Meridian Payments (fintech) · Cedar Health (healthcare) · "
        "Solara Hospitality (renewal at risk) · Ironclad Freight (closed-won expansion). "
        "Event Sales Tech Summit 2026 · campaign Q3 ROI Push._",
        "",
        "**⭐ Recommended walkthrough — copy step by step (≈2 min)**",
        "_The strongest story: role contrast → quantitative dashboard → no-leak → governed access._",
        _cheat_table(["Step", "Command", "What they see"], [
            ["1", "role: employee", "role switch"],
            ["2", "? company brief BluePeak Energy", "public brief, no pricing or competitors"],
            ["3", "role: account-exec", "role switch"],
            ["4", "? company brief BluePeak Energy", "RivalCorp + pricing appear"],
            ["5", "? deal risk BluePeak Energy", "Score 74 · Win 55% · $240k + risk"],
            ["6", "role: head-of-sales", "role switch"],
            ["7", "? pipeline", "dashboard: Total $2,070k · Weighted $1,132k · by stage"],
            ["8", "role: marketing", "role switch"],
            ["9", "? pipeline", "🔒 explicit: figures hidden for marketing (no-leak), needed role named"],
            ["9b", "? content ideas", "marketing's value: 7 ideas from pains (what the role DOES see)"],
            ["10", "role: employee → request access need risk", "request + 🔔 to approvers"],
            ["11", "role: curator → review queue → approve 1 7", "grant for 7 days"],
            ["12", "role: employee → ? deal risk BluePeak Energy", "✅ now visible"],
            ["13", "card BluePeak Energy", "🎬 behind the glass: full card by zone (🔒/✏️/⏳/📜) + closed zones"],
            ["14", "how it works", "🧭 mechanics: card birth, immutability, funnel, governance loop"],
            ["15", "role: account-exec → drive", "📁 connected Google Drive (demo): folders + new resources"],
            ["16", "drive Sales/Q3-Calls → process gd-001", "📥 governed ingest: a proposal, not an edit"],
            ["17", "role: curator → review queue → approve 1 → apply", "ingest goes into the card's Review Needed"],
        ]),
        "_Steps 13–14 \"pull back the curtain\": the source of truth and how the system works "
        "(you can open the same file in Obsidian). Steps 15–17 \"where the data comes from\": "
        "a Drive folder binding → governed ingest through the same approve→apply loop._",
        "_Full catalogue below — every variant you can try._",
        _ROLE_PICKER,
        "",
        "**A. Roles**",
        _cheat_table(["Command", "What it does"], [
            ["roles", "list of all roles and what each one unlocks"],
            ["role: <name>", "employee · sales-rep · account-exec · head-of-sales · revenue-ops"],
            ["", "marketing · legal · curator · admin   (aliases: viewer/ae/hos/sdr/revops)"],
        ]),
        "**B. All question types (with `?`)**",
        _cheat_table(["Message", "What it shows"], [
            ["? company brief BluePeak Energy", "company card"],
            ["? deal risk BluePeak Energy", "risk + Score · Win % · Value of the deal"],
            ["? deal risk all", "cross-view (aggregate for roles without access)"],
            ["? call prep BluePeak Energy", "call preparation"],
            ["? lead priority BluePeak Energy", "lead priority + numeric score"],
            ["? lead priority all", "the whole funnel: MQL/nurture (no deal) → SQL (with a deal)"],
            ["? event brief Sales Tech Summit 2026", "event brief"],
            ["? campaign Q3 ROI Push", "campaign brief"],
            ["? content ideas", "content opportunities (marketing)"],
            ["? my day", "today's tasks for the role"],
            ["? pipeline", "digest + rollup: Total/Weighted/by stage"],
        ]),
        "**B2. Story accounts — the triggers sales/marketing react to** (as `role: head-of-sales`)",
        _cheat_table(["Message", "The story it tells"], [
            ["? deal risk Solara Hospitality", "renewal at risk: champion LEFT, ~45 days to renewal, win 25%"],
            ["? company brief Ironclad Freight", "closed-won proof: dock-to-stock −22%, 12 h/week saved, reference OK"],
            ["? lead priority Cinder Analytics", "intent lead: public G2 complaint about its vendor + RFP hint"],
            ["role: account-exec → ? deal risk Solara Hospitality", "🔒 other team (sales-east) — ABAC, not a bug"],
        ]),
        "**📊 Figures and dashboard — where to look for metrics**",
        _cheat_table(["What you need", "Command", "Who sees the figures"], [
            ["Pipeline dashboard", "? pipeline", "head-of-sales · revenue-ops · admin"],
            ["Score + Win % + Value of a deal", "? deal risk BluePeak Energy", "account-exec (own) · HoS · admin"],
            ["Numeric lead score", "? lead priority BluePeak Energy", "all roles"],
            ["Personal digest", "? my day", "figures — per the role's access"],
            ["PNG chart of the pipeline", "график (chart)", "roles with per-deal figures; others get 🔒"],
            ["PNG chart of lead scores", "график лиды", "all roles"],
            ["PNG client engagement panel", "график BluePeak Energy", "all roles (visits trend, calls held/planned)"],
        ]),
        "_`? pipeline` for HoS/RevOps = dashboard: Open deals · Total pipeline · Weighted (Value×Win%) · "
        "by stage. For marketing/employee the same request arrives WITHOUT figures — that is no-leak, not a bug._",
        "**C. Access contrast (one question — different roles)**",
        _cheat_table(["Role", "Message", "Result"], [
            ["employee", "? company brief BluePeak Energy", "signal + ROI 14h/30d, no pricing"],
            ["marketing", "? company brief BluePeak Energy", "the same signals as a content angle"],
            ["account-exec", "? company brief BluePeak Energy", "+ competitor (RivalCorp) + pricing"],
            ["admin", "? company brief BluePeak Energy", "everything, including personal-data"],
            ["employee", "? deal risk BluePeak Energy", "🔒 no access"],
            ["account-exec / head-of-sales", "? deal risk BluePeak Energy", "full deal risk"],
            ["marketing", "? deal risk all", "aggregate without names"],
            ["account-exec", "? deal risk Northstar Robotics", "🔒 other team (ABAC)"],
            ["head-of-sales / admin", "? deal risk Northstar Robotics", "sees it (above team level)"],
            ["employee", "? call prep BluePeak Energy", "sanitized"],
            ["account-exec", "? call prep BluePeak Energy", "in full"],
        ]),
        "**D. No-leak (the secret does not leak, even if you ask directly)**",
        _cheat_table(["Role", "Message", "Result"], [
            ["employee", "? company brief BluePeak Energy", "no RivalCorp/pricing (in Restricted)"],
            ["account-exec", "? company brief BluePeak Energy", "RivalCorp and pricing appear"],
        ]),
        "_Filtering by construction: the role decides what to extract — not \"hope they don't ask\"._",
        "**E. Honesty and provenance**",
        _cheat_table(["Message / where", "What is visible"], [
            ["bottom of any answer", "📎 Sources + Confidence/Freshness/As of"],
            ["? company brief Tesla", "honest not-found (invents nothing)"],
        ]),
        "**F. Request → approve → grant → revoke (governance)**",
        _cheat_table(["Step", "Message", "Result"], [
            ["1", "role: employee → ? deal risk BluePeak Energy", "🔒"],
            ["2", "request access need risk", "proposal-0001 + 🔔 to approvers"],
            ["3", "role: curator → review queue → approve 1 7", "grant for 7 days"],
            ["4", "role: employee → ? deal risk BluePeak Energy", "✅ now visible"],
            ["5", "? deal risk Atlas Foods", "🔒 the grant is scoped"],
            ["6", "role: curator → revoke 1 not needed", "🔒 again for employee"],
            ["–", "role: curator → reject 1 reason", "rejection"],
            ["–", "approve under role: admin", "then employee sees personal-data too"],
        ]),
        "**F2. Three proposal types → review queue → apply**",
        _cheat_table(["Message", "What it does"], [
            ["request access <reason>", "request access to a company's closed data"],
            ["flag stale <note>", "flag \"data is stale/wrong\" → into the review queue"],
            ["request redaction <reason>", "request to review/hide personal data"],
            ["apply", "a reviewer runs the single-writer worker → edit into Review Needed"],
        ]),
        "_Full flag/redaction cycle: `flag stale …` → `role: curator` → "
        "`approve 1` → `apply` — the worker (a separate process) writes the edit into the "
        "card's Review Needed section; the gateway itself writes nothing._",
        "**G. Marketing and daily views**",
        _cheat_table(["Role", "Message"], [
            ["marketing", "? campaign Q3 ROI Push · ? content ideas"],
            ["account-exec", "? my day"],
            ["head-of-sales", "? pipeline"],
        ]),
        "**G2. Data sources — Google Drive (demo, governed ingest)**",
        "_A synthetic connector (no OAuth). Folders are visible per role (no-leak); "
        "\"process\" does not write a card but creates a proposal into the same loop._",
        _cheat_table(["Command", "What it does"], [
            ["drive", "connected folders + new-resource counter"],
            ["drive Sales/Q3-Calls", "folder resources (🆕/✅); a closed zone → 🔒"],
            ["process gd-001", "ingest_resource proposal → review queue"],
            ["process all", "a proposal for each new file in the accessible folders"],
        ]),
        "",
        "**H. Tables, charts, files, reset**",
        _cheat_table(["Command", "What it does"], [
            ["chart", "ASCII chart of the current role's access across tools"],
            ["file company brief BluePeak Energy", "export the answer as a .md file"],
            ["file deal risk BluePeak Energy csv", "export the table as a .csv"],
            ["clear history yes", "demo reset: delete the chat history (irreversible; confirm with `yes`)"],
        ]),
        "_Questions take `?`; commands (role:/request/approve/revoke/…) do not. "
        "This cheat-sheet — command `demo`._",
    ]
    return "\n".join(parts)


def lifecycle_help() -> str:
    """`как это работает` — the 'how the system actually works' explainer that pairs
    with the `карточка` reveal: card birth, immutability of the controlled core, the
    governance write-loop and state transitions (funnel + freshness)."""
    funnel = _cheat_table(["Transition", "What it means"], [
        ["prospect → MQL", "interest appeared, the lead is qualifying (marketing)"],
        ["MQL → SQL", "the lead is accepted into the sales funnel (sales)"],
        ["SQL → deal", "a deal is created, then the deal stages follow"],
        ["fresh → stale", "the card has not been reviewed beyond the freshness window"],
    ])
    gov = _cheat_table(["Step", "Command / mechanism"], [
        ["1. propose", "`request access` / `flag stale` / `request redaction`"],
        ["2. into the queue", "the edit lands in the card's **Review Needed** section"],
        ["3. approve", "curator: `review queue` → `approve <id>`"],
        ["4. apply", "`apply` → the single-writer worker writes the edit into the card"],
        ["5. audit", "a line is added to **Change History**"],
    ])
    return "\n".join([
        "🧭 **How the system works — the card lifecycle**",
        "",
        "**1. Birth.** A card is created by the chokepoint `scripts/new_entity.py`: it mints a "
        "typed-ULID id into the append-only `state/id-ledger.jsonl`, stamps `created` / "
        "`template_version` and expands the sections from the template. The ID cannot be hand-authored.",
        "",
        "**2. Immutability.** The **Controlled Profile** section is protected by `profile_lock`. "
        "A direct edit is not applied — it is only *proposed* and waits for curator approval (fail-safe).",
        "",
        "**3. State transitions.** Lead funnel and card freshness:",
        funnel,
        "",
        "**4. Governance loop** — how an edit actually reaches a card:",
        gov,
        "",
        "_`card <company>` shows the full card as-is, by zone. "
        "Per-role scenarios — `demo <role>`._",
    ])


def _normalize_pid(token: str) -> str:
    """Accept `proposal-0001`, `0001` or `1` as a proposal id."""
    token = token.strip().strip("`").strip()
    return f"proposal-{int(token):04d}" if token.isdigit() else token


def _strip_command_prefix(text: str, prefixes: tuple[str, ...]) -> str:
    """Return the argument after a matched command prefix (longest match first so
    `пометить устаревшим` wins over the bare `пометить`)."""
    low = text.lower()
    for prefix in sorted(prefixes, key=len, reverse=True):
        if low.startswith(prefix):
            return text[len(prefix):].strip(" :-—")
    return text


def handle(text: str, state: dict, wiki: Wiki) -> "str | dict | None":
    """Map one chat message to a reply: a string to post, a {"upload": artifact}
    dict to upload as a file, or None if it isn't addressed to the bot."""
    stripped = text.strip()
    low = stripped.lower()
    trigger = state["trigger"]

    if low.startswith(("роль:", "role:")):
        wanted = stripped.split(":", 1)[1].strip()
        canonical = resolve_role(wanted)
        if canonical:
            state["role"] = canonical
            msg = f"✅ OK, your role is now `{canonical}`. {ROLES[canonical][1]}"
            pending = wiki.pending_count(canonical)  # push: tell a reviewer there's work
            if pending:
                msg += f"\n🔔 {pending} request(s) await your decision — `review queue`."
            return msg
        return f"❓ I don't know role `{wanted}`. Available: {', '.join(ROLES)}. List — `roles`."

    # `/demo` is usually swallowed by Rocket.Chat's slash-command system; `демо`
    # (no slash) is the reliable trigger, with a few aliases.
    # `демо` = full catalogue; `демо <роль>` = focused per-role walkthrough.
    demo_body = stripped.lstrip("/").strip()
    if demo_body.lower().startswith(trigger):
        demo_body = demo_body[len(trigger):].strip()
    demo_parts = demo_body.split(maxsplit=1)
    if demo_parts and demo_parts[0].lower() in {"демо", "demo"}:
        role_arg = demo_parts[1].strip() if len(demo_parts) > 1 else ""
        sub, _, sub_rest = role_arg.lower().partition(" ")
        if sub in {"старт", "start"}:
            try:
                delay = max(2, int(sub_rest.strip() or "10"))
            except ValueError:
                delay = 10
            return {"autoplay": delay}
        if sub in {"стоп", "stop"}:
            wiki.autoplay_stop.set()
            return "⏹ Autopilot stop requested — it halts at the next beat."
        if not role_arg:
            return demo_help()
        canonical = resolve_role(role_arg)
        if canonical:
            return _role_demo(canonical)
        return (f"❓ I don't know role `{role_arg}`. Available: {', '.join(ROLES)}. "
                f"Full catalogue — `demo`.")

    if low in {"роли", "roles", "help", "справка", f"{trigger}help", f"{trigger}роли"}:
        return roles_help()

    # Destructive demo-reset: clears the chat history. Matched by EXACT command
    # forms (not a broad `clear` prefix that would swallow "clearance report").
    # Two-step by design — a bare command only warns; an explicit confirm token
    # deletes. In the demo the role is self-assigned, so the confirm step (not a
    # role gate) is the real guard against an accidental wipe.
    _clear_bases = {"очистить историю", "очистить", "clear history", "clear"}
    _clear_command = low.strip()
    _clear_confirmed = False
    for _token in (" да", " yes", " confirm"):
        if _clear_command.endswith(_token):
            _clear_command = _clear_command[: -len(_token)].strip()
            _clear_confirmed = True
            break
    if _clear_command in _clear_bases:
        if _clear_confirmed:
            return {"clear_history": True}
        return (
            "⚠️ This will delete the ENTIRE chat history — irreversible (in a self-DM all "
            "messages are deleted; in a shared channel only the bot's messages). Confirm: `clear history yes`."
        )

    access_prefixes = ("запросить доступ", "запрос доступа", "request access")
    if low.startswith(access_prefixes):
        reason = stripped
        for prefix in access_prefixes:
            if low.startswith(prefix):
                reason = stripped[len(prefix):].strip(" :-—")
                break
        name = state["company_name"]
        reason = reason or f"role {state['role']} requests access to {name}"
        pid = wiki.request_access(state["role"], state["company_id"], reason)
        return (
            f"📨 Access request created: `{pid}` (source: {name}).\n"
            f"🔔 Approvers (`curator`/`hos`/`admin`): a decision is needed — "
            f"`review queue` → `approve {pid}` / `reject {pid} <reason>`."
        )

    flag_prefixes = ("пометить устаревшим", "пометить неверным", "пометить устаревш",
                     "пометить неверн", "flag stale", "пометить")
    if low.startswith(flag_prefixes):
        name = state["company_name"]
        note = _strip_command_prefix(stripped, flag_prefixes) or \
            f"role {state['role']}: card {name} is stale or incorrect"
        pid = wiki.flag_stale(state["role"], state["company_id"], note)
        return (
            f"🚩 Flagged as stale/incorrect: `{pid}` (card: {name}).\n"
            f"🔔 For curators: `review queue` → `approve {pid}` / `reject {pid} <reason>`."
        )

    redaction_prefixes = ("запросить редактуру", "запросить редакцию", "запрос редактуры",
                          "request redaction", "редактура")
    if low.startswith(redaction_prefixes):
        name = state["company_name"]
        reason = _strip_command_prefix(stripped, redaction_prefixes) or \
            f"role {state['role']}: review personal data in {name}"
        pid = wiki.request_redaction(state["role"], state["company_id"], reason)
        return (
            f"🛡️ Personal-data redaction review requested: `{pid}` (card: {name}).\n"
            f"🔔 For curators / legal / admin: `review queue` → `approve {pid}` / `reject {pid} <reason>`."
        )

    if low in {"очередь", "очередь ревью", "review queue", "queue", f"{trigger}очередь"}:
        return wiki.review_queue(state["role"])

    if low in {"применить", "применить заявки", "apply", "worker", f"{trigger}применить"}:
        return wiki.apply_proposals(state["role"])

    if low.startswith(("одобрить", "approve")):
        toks = stripped.split()
        pid = _normalize_pid(toks[1]) if len(toks) > 1 else ""
        ttl = int(toks[2]) if len(toks) > 2 and toks[2].isdigit() else None
        return wiki.decide(state["role"], "approve", pid, ttl_days=ttl)

    if low.startswith(("отклонить", "reject")):
        rest = stripped.split(maxsplit=2)
        pid = _normalize_pid(rest[1]) if len(rest) > 1 else ""
        reason = rest[2] if len(rest) > 2 else ""
        return wiki.decide(state["role"], "reject", pid, reason)

    if low.startswith(("отозвать", "revoke")):
        rest = stripped.split(maxsplit=2)
        pid = _normalize_pid(rest[1]) if len(rest) > 1 else ""
        reason = rest[2] if len(rest) > 2 else ""
        return wiki.decide(state["role"], "revoke", pid, reason)

    if low.startswith(("как это работает", "как работает", "жизненный цикл",
                        "how it works", "how the system works", "lifecycle")):
        return lifecycle_help()

    if low.startswith(("карточка", "card ", "закулисье", "xray")) or low in {"card", "карточка"}:
        rest = stripped.split(maxsplit=1)
        spec = rest[1].strip() if len(rest) > 1 else ""
        name = (wiki.detect_company(spec) if spec else None) or state.get("company_name")
        if not name:
            return ("Which card should I show? Example: `card Atlas Foods`. "
                    f"Companies: {', '.join(DEMO_COMPANIES)}.")
        return wiki.card_xray(state["role"], name)

    if low.startswith(("драйв", "drive", "гугл драйв", "google drive")):
        rest = stripped.split(maxsplit=1)
        folder = rest[1].strip() if len(rest) > 1 else ""
        # strip an English "drive"/"google drive" lead-in so `drive Sales/...` works
        for lead in ("гугл драйв", "google drive", "драйв", "drive"):
            if folder.lower().startswith(lead):
                folder = folder[len(lead):].strip()
        return wiki.drive_folder(state["role"], folder) if folder else wiki.drive_folders(state["role"])

    if low.startswith(("обработать", "process", "запроцессить", "ингест", "ingest")):
        rest = stripped.split(maxsplit=1)
        spec = rest[1].strip() if len(rest) > 1 else ""
        if not spec:
            return ("What should I process? Example: `process gd-001` or `process all`. "
                    "First look at the resources: `drive <folder>`.")
        return wiki.drive_process(state["role"], spec)

    if low.startswith(("график", "graph", "chart")):
        rest = stripped.split(maxsplit=1)
        return wiki.chart(state["role"], rest[1].strip() if len(rest) > 1 else "")

    if low.startswith(("диаграмма", "diagram")):
        return wiki.access_chart(state["role"])

    if low.startswith(("файл", "file", "скачать", "download")):
        rest = stripped.split(maxsplit=1)
        spec = rest[1].strip() if len(rest) > 1 else ""
        if not spec:
            return "What should I export? Example: `file company brief BluePeak Energy` or `file deal risk csv`."
        artifact = wiki.file_artifact(state["role"], spec)
        return {"upload": artifact} if isinstance(artifact, dict) else artifact

    if stripped.startswith(trigger):
        question = stripped[len(trigger):].strip()
        if not question:
            return roles_help()
        name = wiki.detect_company(question)
        if name:
            state["company_name"] = name
            state["company_id"] = wiki.company_id(name)
        return wiki.answer(state["role"], question)

    return None  # not a command/question for the bot — ignore


def main() -> int:
    try:
        allow_legacy = os.environ.get("SALESWIKI_ALLOW_LEGACY_RC", "").lower() in {
            "1", "true", "yes", "on"
        }
        settings = load_runtime_settings(allow_legacy=allow_legacy)
        adapter = settings.enabled_adapter("rocketchat")
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    base = adapter.env_value(os.environ, adapter.endpoint_env)
    user = adapter.env_value(os.environ, adapter.user_env)
    credential = adapter.env_value(os.environ, adapter.password_env)
    channel = adapter.conversation
    dm = adapter.direct_message
    missing = adapter.missing_secret_refs(os.environ)
    if missing:
        print(f"Missing runtime environment values: {', '.join(missing)}", file=sys.stderr)
        return 2

    def new_session() -> dict:
        return {
            "role": DEFAULT_ROLE,
            "trigger": adapter.trigger or settings.chat.default_trigger,
            "company_name": "BluePeak Energy",
            "company_id": "demo-company-bluepeak-energy",
        }
    poll = adapter.poll_seconds

    print("Generating demo vault + service…")
    wiki = Wiki(settings)
    rc = RocketChat(base, user, credential)
    rc.login()
    if dm:
        room_id, kind = rc.resolve_dm(dm)
        target = f"DM:{dm}" + (" (self)" if dm == user else "")
    else:
        room_id, kind = rc.resolve_room(channel)
        target = f"#{channel}"
    trigger = adapter.trigger or settings.chat.default_trigger
    print(f"Logged in as {user}; watching {target} ({kind}/{room_id}). Trigger='{trigger}'.")

    # Ignore any backlog: start from the newest existing message timestamp.
    backlog = rc.history(kind, room_id, "1970-01-01T00:00:00.000Z")
    last_ts = backlog[-1]["ts"] if backlog else now_iso()
    rc.post(room_id, demo_help())

    print("Bridge running. Ctrl-C to stop.")
    autoplay_thread: "threading.Thread | None" = None

    transport = RocketChatTransport(
        rc,
        tenant_id=base,
        conversation_id=room_id,
        conversation_kind=kind,
    )

    def start_demo(delay: float, state: dict) -> None:
        nonlocal autoplay_thread
        if autoplay_thread and autoplay_thread.is_alive():
            rc.post(room_id, "▶️ Autopilot is already running — `демо стоп` to halt it.")
            return
        wiki.autoplay_stop.clear()
        autoplay_thread = threading.Thread(
            target=run_autoplay,
            args=(rc, room_id, wiki, state, delay),
            daemon=True,
        )
        autoplay_thread.start()

    runtime = ChatRuntime(
        transport,
        lambda text, session: handle(text, session, wiki),
        new_session,
        decorate_text=with_separator,
        start_demo=start_demo,
    )
    while True:
        try:
            last_ts = runtime.poll_once(last_ts)
            time.sleep(poll)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except Exception as exc:  # keep the demo alive on transient API hiccups
            print(f"[warn] {exc}", file=sys.stderr)
            time.sleep(poll)
