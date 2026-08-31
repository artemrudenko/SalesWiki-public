"""Shared constants and pure helpers for the Rocket.Chat demo bridge."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from integrations.chat.rendering import split_markdown  # noqa: E402
from saleswiki_mcp import config  # noqa: E402

# Some WAFs in front of Rocket.Chat reset the default Python-urllib User-Agent;
# posing as a browser keeps the demo bridge compatible with those deployments.
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Friendly chat role name -> (demo actor id, one-line description of what it unlocks).
# Full, non-jargon English role names (keep marketing/sales/etc. clearly distinct).
ROLES: dict[str, tuple[str, str]] = {
    "employee": ("demo-broad-viewer", "Employee: general public cards, no sales-confidential."),
    "sales-rep": ("demo-sam-sdr", "Sales Rep (SDR): general access, no private deal details and no deal risk."),
    "account-exec": ("demo-ivan-ae", "Account Executive (account owner): pricing, competitor intel, deal risk on own deals."),
    "head-of-sales": ("demo-elena-hos", "Head of Sales: deal risk and pipeline across the whole team."),
    "revenue-ops": ("demo-raj-revops", "Revenue Ops: deal risk and operational pipeline data."),
    "marketing": ("demo-nina-marketing", "Marketing: aggregated/sanitized data, market signals, content opportunities; no secrets."),
    "legal": ("demo-lena-legal", "Legal: limited access, personal-data review; no commercial secrets."),
    "curator": ("demo-marina-curator", "Knowledge Curator: governance, review queue, proposal approvals."),
    "admin": ("demo-ada-admin", "Admin: full access to everything."),
}
DEFAULT_ROLE = "employee"

# The boundaries visible in bridge-side gates (folder listing/ingest, x-ray
# hints). The closed tiers users can request/unlock; other policy boundaries
# (legal-review, operational-state, ...) have no bridge surface.
_HINTED_BOUNDARIES = ("sales-confidential", "personal-data")


def _derive_boundary_maps() -> tuple[dict[str, set[str]], dict[str, list[str]], dict[str, str]]:
    """Derive the bridge's role→boundary gating from the CANONICAL access policy
    (schemas/access-policy.json) via each demo actor's fixture role — never a
    hardcoded shadow copy that could drift from what the gateway enforces.

    Returns (role_boundaries, unlock_roles, audience):
    - role_boundaries: chat role -> exact boundary set of its policy role;
    - unlock_roles: per closed boundary, up to three chat roles named in 🔒
      hints. Roles whose access is `assigned`-constrained are skipped — switching
      to them unlocks nothing by itself, so they are not an honest hint;
    - audience: per-boundary legend naming every role that may see the zone.
    """
    policy_roles = {r["id"]: r for r in config.access_policy().get("roles", [])}
    actor_role = {u["id"]: u.get("role", "")
                  for u in config.identity_config()["providers"]["fixture"]["users"]}
    role_boundaries: dict[str, set[str]] = {}
    constraints: dict[str, dict[str, str]] = {}
    for chat_role, (actor_id, _desc) in ROLES.items():
        policy_role = policy_roles.get(actor_role.get(actor_id, ""), {})
        # Fail closed: an unmapped actor sees only the broad tier.
        role_boundaries[chat_role] = set(policy_role.get("boundaries", ["broad"]))
        constraints[chat_role] = policy_role.get("attribute_constraints", {})
    unlock: dict[str, list[str]] = {}
    audience: dict[str, str] = {"broad": "visible to all employees"}
    for boundary in _HINTED_BOUNDARIES:
        holders = [r for r in ROLES if boundary in role_boundaries[r]]
        unlock[boundary] = [r for r in holders if constraints[r].get(boundary) != "assigned"][:3]
        audience[boundary] = ("only " + " / ".join(holders)) if holders else "no role"
    return role_boundaries, unlock, audience


# All three maps come from schemas/access-policy.json (see _derive_boundary_maps);
# no authorization decision in the bridge is allowed to use a hardcoded map.
ROLE_BOUNDARIES, BOUNDARY_UNLOCK_ROLES, BOUNDARY_AUDIENCE = _derive_boundary_maps()


def _missing_boundaries(role: str) -> list[str]:
    """Boundaries the role cannot see (broad is always visible)."""
    seen = ROLE_BOUNDARIES.get(role, {"broad"})
    return [b for b in _HINTED_BOUNDARIES if b not in seen]


def _unlock_hint(boundaries: list[str]) -> str:
    """Human hint naming which role unlocks each withheld boundary."""
    bits = []
    for b in boundaries:
        roles = " / ".join(f"`{r}`" for r in BOUNDARY_UNLOCK_ROLES[b])
        bits.append(f"{b} → {roles}")
    return "; ".join(bits)

# Short/legacy aliases + Russian names so habit, older scripts and Russian
# chat ("демо маркетинг", "роль: куратор") all resolve to a canonical role.
ROLE_ALIASES: dict[str, str] = {
    "viewer": "employee", "broad-viewer": "employee", "broad": "employee",
    "sdr": "sales-rep", "sales": "sales-rep", "rep": "sales-rep",
    "ae": "account-exec", "account-executive": "account-exec",
    "hos": "head-of-sales", "head_of_sales": "head-of-sales",
    "revops": "revenue-ops", "rev-ops": "revenue-ops",
    # Russian role words
    "сотрудник": "employee", "сейлз": "sales-rep", "продавец": "account-exec",
    "менеджер": "account-exec", "руководитель": "head-of-sales",
    "маркетинг": "marketing", "маркетолог": "marketing",
    "юрист": "legal", "куратор": "curator",
    "админ": "admin", "администратор": "admin",
}

# The summary headline prefix on substantive read answers. Shared with the live
# smoke test (smoke_test.py) so its presence check cannot silently go dead when
# the wording changes.
SUMMARY_MARKER = "🤖 Summary"
RECS_MARKER = "🧠 Recommendations (AI-generated from the cited data above):"
# Appended to every posted answer so consecutive replies don't blend together.
SEPARATOR = "─" * 40


def with_separator(text: str) -> str:
    return f"{text}\n{SEPARATOR}"


MAX_MESSAGE_CHARS = 4500  # Rocket.Chat's default Message_MaxAllowedSize is 5000


def split_message(text: str, limit: int = MAX_MESSAGE_CHARS) -> list[str]:
    """Compatibility wrapper for callers of the former Rocket.Chat helper."""
    return split_markdown(text, limit)

# Known demo entities, matched in question text to fill a tool's argument.
DEMO_COMPANIES = ["BluePeak Energy", "Atlas Foods", "Northstar Robotics", "Meridian Payments", "Cedar Health",
                  "Solara Hospitality", "Ironclad Freight",
                  "Vertex Logistics", "Lumen Retail", "Orchard Bank", "Cinder Analytics"]  # last 4 = top-of-funnel prospects
DEMO_EVENTS = ["Sales Tech Summit 2026"]
DEMO_CAMPAIGNS = ["Q3 ROI Push"]

# The `карточка` reveal annotates a card's governance sections. Order = render order.
XRAY_ZONES = {
    "Controlled Profile": ("🔒", "protected core; changeable only via curator review (profile_lock)"),
    "Live Intelligence": ("✏️", "working area — research and analysis land here"),
    "Review Needed": ("⏳", "queue of proposed edits — awaiting approval"),
    "Change History": ("📜", "audit trail: who changed what and when"),
}
# The teaching legend for the reveal (which roles see each access zone) is
# BOUNDARY_AUDIENCE above — derived from the access policy, never hardcoded.


def resolve_role(name: str) -> str | None:
    """Map a typed role (full name or short alias) to a canonical role key."""
    name = name.strip().lower()
    if name in ROLES:
        return name
    return ROLE_ALIASES.get(name)


# Intent routing: ordered (specific first); each maps keywords -> a read tool.
# tool spec = (service method, argument kind). arg kinds: "company" | "event" |
# "campaign" | None (no argument).
INTENTS: list[tuple[list[str], str, str | None]] = [
    (["pipeline", "пайплайн", "дайджест", "digest"], "pipeline_risk_digest", None),
    (["my day", "мой день", "что делать", "сегодня"], "my_day", None),
    (["контент", "content", "opportunit", "идеи"], "content_opportunities", None),
    (["звон", "подготов", "call prep", "call"], "call_prep", "company"),
    (["событ", "event", "конференц", "summit"], "event_brief", "event"),
    (["кампан", "campaign"], "campaign_brief", "campaign"),
    (["лид", "lead", "приорит"], "lead_priority", "company"),
    (["риск", "risk", "сделк", "deal"], "deal_risk", "company"),
    (["бриф", "brief", "компан", "company", "профил"], "company_brief", "company"),
]


# Entity-name candidate tokens: a capitalized (Latin/Cyrillic) word, or a
# digit-led token that can continue a name ("Summit 2026", "Q3 ROI Push").
_NAME_TOKEN = re.compile(r"[A-ZА-ЯЁ][\w&'.\-]*|\d[\w&'.\-]*")
# Capitalized words that are command/intent vocabulary, not entity names
# ("Бриф по Acme" -> only "Acme" is a name candidate).
_ARG_STOPWORDS = {"по", "про", "для", "и", "в", "на", "the", "a", "an", "for",
                  "of", "to", "дай", "покажи", "give", "show", "me", "all", "все", "всё"}
_INTENT_STEMS = tuple({stem for keywords, _method, _arg in INTENTS
                       for phrase in keywords for stem in phrase.split()})


def _explicit_name_tokens(text: str) -> list[str]:
    """Tokens the user most likely typed as an explicit entity name: capitalized
    (or numeric) words minus intent/command vocabulary. Empty when the question
    names nothing ("дай бриф")."""
    tokens: list[str] = []
    for tok in _NAME_TOKEN.findall(text):
        low = tok.lower()
        if len(low) < 2 or low in _ARG_STOPWORDS:
            continue
        if any(low.startswith(stem) for stem in _INTENT_STEMS):
            continue
        tokens.append(tok)
    # Digit-led tokens only ever continue a name; alone they are not one.
    return tokens if any(t[0].isalpha() for t in tokens) else []


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# Vars a spawned child (MCP server / worker) legitimately needs. Deliberately
# excludes chat credentials (RC_USER/RC_PASS) and the model key (ANTHROPIC_API_KEY):
# the children never reach Rocket.Chat or a model, so forwarding the whole parent
# environment only widens the secret's exposure surface.
_CHILD_ENV_PASSTHROUGH = (
    "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SSL_CERT_FILE",
    "SALESWIKI_APPROVAL_KEY", "SALESWIKI_ALLOW_PROD_VAULT",
)


def _child_env(**overrides: str) -> dict:
    """A minimal environment for a spawned MCP-server/worker child: only the vars
    it needs to run plus the given SALESWIKI_* overrides — never the bridge's chat
    or model secrets."""
    env = {k: os.environ[k] for k in _CHILD_ENV_PASSTHROUGH if k in os.environ}
    env.update(overrides)
    return env
