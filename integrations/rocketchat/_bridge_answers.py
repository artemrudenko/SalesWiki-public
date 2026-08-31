"""Answer routing, rendering and chart presentation for the chat bridge."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections import Counter

import chartpng
from _bridge_common import *  # noqa: F403
from _bridge_common import (
    _child_env,
    _explicit_name_tokens,
    _missing_boundaries,
    _unlock_hint,
)


class WikiAnswerMixin:
    @staticmethod
    def _match_arg(text: str, kind: str, default_first: bool = True) -> str | None:
        catalog = {"company": DEMO_COMPANIES, "event": DEMO_EVENTS, "campaign": DEMO_CAMPAIGNS}[kind]
        low = text.lower()
        for name in catalog:
            if name.lower() in low:
                return name
        # An explicit name was typed but is not a known full name: resolve a
        # unique partial match ("бриф Atlas" -> Atlas Foods), otherwise pass the
        # raw name through so the service's honest Answer-envelope not-found is
        # what the user sees — never a silent default to catalog[0] ("? бриф по
        # Acme Industrial" must not become a BluePeak Energy brief).
        candidates = _explicit_name_tokens(text)
        if candidates:
            hits = {name for name in catalog
                    if any(t.lower() in name.lower() for t in candidates)}
            if len(hits) == 1:
                return hits.pop()
            return " ".join(candidates)
        # Nothing explicit named: a sensible default so a bare "дай бриф" still
        # demos something; callers with an all-items view pass default_first=False.
        return catalog[0] if default_first else None

    def _match_intent(self, question: str):
        """Map a free-text question to (method, arg_kind, arg) or None."""
        low = question.lower()
        for keywords, method, arg_kind in INTENTS:
            if any(k in low for k in keywords):
                if arg_kind is None:
                    return (method, None, None)
                if arg_kind == "company" and method in ("deal_risk", "lead_priority"):
                    # No company named -> the all-items view (full funnel / all deals),
                    # not a surprise default to the first company. "все"/"all" also lands here.
                    return (method, arg_kind, self._match_arg(question, arg_kind, default_first=False))
                return (method, arg_kind, self._match_arg(question, arg_kind))
        return None

    def _route(self, role: str, question: str) -> dict | None:
        """In-process: route a question to a read tool and return its envelope."""
        intent = self._match_intent(question)
        if intent is None:
            return None
        method, arg_kind, arg = intent
        actor = self.actor(role)
        if arg_kind is None:
            return getattr(self.svc, method)(actor)
        return getattr(self.svc, method)(actor, arg)

    _NOT_UNDERSTOOD = (
        "🤔 I didn't understand the request. Examples: `? company brief BluePeak Energy`, "
        "`? deal risk`, `? my day`, `? pipeline`. List of roles — command `roles`."
    )

    def answer(self, role: str, question: str) -> str:
        if self.use_mcp:
            return self._answer_via_mcp(role, question)
        intent = self._match_intent(question)
        if intent is None:
            return self._NOT_UNDERSTOOD
        env = self._route(role, question)
        if env is None:
            return self._NOT_UNDERSTOOD
        rendered = self._render(role, env)
        rendered += self._llm_recommendations(env, intent[0])
        # If the answer contains record cards, tell the user the command that
        # generates + uploads the same data as a file (no pre-made link exists).
        if "```" in rendered:
            rendered += f"\n📎 Need a file? Send: `file {question} csv` — I'll post a .csv to the chat."
        return rendered

    # -- MCP mode: route reads through the stdio MCP server (server.py) ---------
    _MCP_PARAM = {
        "company_brief": "company", "deal_risk": "company", "call_prep": "company",
        "lead_priority": "company", "event_brief": "event", "campaign_brief": "campaign",
        "content_opportunities": "scope", "my_day": "scope", "pipeline_risk_digest": "scope",
    }

    def _answer_via_mcp(self, role: str, question: str) -> str:
        intent = self._match_intent(question)
        if intent is None:
            return self._NOT_UNDERSTOOD
        method, _arg_kind, arg = intent
        tool = f"saleswiki.{method}"
        kwargs = {self._MCP_PARAM[method]: arg} if arg else {}
        try:
            text, data = asyncio.run(self._mcp_call(ROLES[role][0], tool, kwargs))
        except Exception as exc:  # surface MCP failures instead of silent empty
            return f"⚠️ MCP call failed: {exc}"
        return self._render_mcp(role, text, question, data.get("access", ""))

    async def _mcp_call(self, actor_id: str, tool: str, kwargs: dict) -> tuple[str, dict]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = _child_env(
            SALESWIKI_DEMO_ACTOR=actor_id,
            SALESWIKI_VAULT_ROOT=str(self.vault_root),
            SALESWIKI_RUNTIME_DIR=str(self.runtime),
            PYTHONPATH=str(ROOT),
        )
        params = StdioServerParameters(command=sys.executable, args=["-m", "saleswiki_mcp.server"], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, kwargs)
                text = "".join(getattr(c, "text", "") for c in result.content)
                # Envelope semantics (access/status/reason/proposal_id) ride in
                # structuredContent; the text stays presentation-only.
                return text, (result.structuredContent or {})

    def _render_mcp(self, role: str, text: str, question: str, access: str = "") -> str:
        header = f"🤖 **SalesWiki** · role `{role}` · via MCP"
        text = self._shorten_sources_text(text)
        text, stripped = self._strip_restricted_sections(text)
        text = self._friendly_headings(text)
        text, locked = self._format_tables(text)
        if access == "blocked":
            return self._blocked_message(role, question)
        notice = (self._access_notice(role, abac_masked=locked)
                  if (locked or stripped or access in {"sanitized", "aggregated"}) else "")
        out = f"{header}{notice}\n\n{self._readable_spacing(text.strip())}"
        if "```" in out:
            out += f"\n\n📎 Need a file? Send: `file {question} csv` — I'll post a .csv to the chat."
        return out

    @staticmethod
    def _shorten_sources_text(text: str) -> str:
        """Shorten a raw `**Sources:** boundary: path; ...` line to card titles."""
        out = []
        for line in text.split("\n"):
            if line.startswith("**Sources:**"):
                titles: list[str] = []
                for item in line[len("**Sources:**"):].split(";"):
                    item = item.strip()
                    if not item or "://" in item:
                        continue  # restricted handle
                    path = item.split(":", 1)[-1].strip()
                    name = path.rsplit("/", 1)[-1]
                    if name.endswith(".md"):
                        name = name[:-3]
                    name = name.replace(" - ", " — ")
                    if name and name not in titles:  # dedup
                        titles.append(name)
                if titles:  # one source per line for readability
                    listing = "\n".join(f"   - {t}" for t in titles)
                    out.append(f"📎 Sources ({len(titles)}):\n{listing}")
            else:
                out.append(line)
        return "\n".join(out)

    def file_artifact(self, role: str, question: str):
        """Build a downloadable artifact from a role-gated answer. Returns a dict
        (filename/content/ctype/caption) to upload, or a str message to post
        (unknown request, or a blocked/no-access answer)."""
        env = self._route(role, question)
        if env is None:
            return ("🤔 I didn't understand what to export. Example: `file company brief BluePeak Energy` "
                    "or `file deal risk csv`.")
        if env.get("access") == "blocked":
            return self._render(role, env)  # the friendly 🔒 message, not a file
        title = env.get("title", "SalesWiki")
        base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "saleswiki"
        caption = f"📎 {title} · role `{role}`"
        if "csv" in question.lower():
            table = next((s.get("table") for s in env.get("sections", []) if s.get("table")), None)
            if table:
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(table.get("columns", []))
                writer.writerows(table.get("rows", []))
                return {"filename": f"{base}.csv", "content": buf.getvalue().encode("utf-8"),
                        "ctype": "text/csv", "caption": caption}
        return {"filename": f"{base}.md", "content": env.get("text", "").encode("utf-8"),
                "ctype": "text/markdown", "caption": caption}

    def chart(self, role: str, arg: str) -> "dict | str":
        """`график [пайплайн|лиды|<company>]` — dispatch to the chart variants."""
        a = arg.strip().lower()
        if a in ("", "пайплайн", "pipeline"):
            return self.pipeline_chart(role)
        if a in ("лиды", "лид", "приоритет", "leads", "priority"):
            return self.leads_chart(role)
        name = self.detect_company(arg)
        if name:
            return self.client_stats_chart(role, name)
        return ("📈 Which chart? `график` — pipeline by deal; `график лиды` — lead "
                "scores; `график <company>` — client engagement (visits, calls).")

    def leads_chart(self, role: str) -> "dict | str":
        """Lead-priority scores as a PNG, from the same lead_priority envelope
        as the text answer (every role may read leads)."""
        env = self.svc.lead_priority(self.actor(role), "")
        if env.get("access") == "blocked":
            return self._blocked_message(role, env.get("title", "Lead Priority"))
        rows: list[tuple[str, int, str]] = []
        for sec in env.get("sections", []):
            table = sec.get("table") or {}
            cols = table.get("columns") or []
            if "Lead" in cols and "Score" in cols and "Score band" in cols:
                i_l, i_s, i_b = cols.index("Lead"), cols.index("Score"), cols.index("Score band")
                for r in table.get("rows", []):
                    digits = re.sub(r"\D", "", r[i_s])
                    if digits:
                        rows.append((r[i_l], int(digits), r[i_b]))
        if not rows:
            return f"🔒 Role `{role}` sees no lead scores to draw."
        png = chartpng.leads_chart_png(rows, role, env.get("as_of", ""))
        caption = (f"📊 Lead priority — {len(rows)} lead(s) by score; dark = hot. "
                   f"Role `{role}` · built from cited lead cards.")
        return {"upload": {"filename": f"leads-{role}.png", "content": png,
                           "ctype": "image/png", "caption": caption}}

    def client_stats_chart(self, role: str, name: str) -> "dict | str":
        """Client engagement panel (visits trend + calls) from the broad-zone
        company card's Engagement Snapshot — safe for every role, cited."""
        path = (self.vault_root / "broad" / "wiki" / "entities" / "companies"
                / f"Company - {name}.md")
        if not path.exists():
            return f"🤔 No card found for \"{name}\" in the demo vault."
        _fm, sections, _order = self._read_card(path)
        block = "\n".join(sections.get("Engagement Snapshot", []))
        visits_m = re.search(r"visits[^:]*:\s*([\d,\s]+)", block, re.I)
        held_m = re.search(r"held[^:]*:\s*(\d+)", block, re.I)
        planned_m = re.search(r"planned:\s*(\d+)\s*\(next:\s*([0-9-]+)", block, re.I)
        if not (visits_m and held_m and planned_m):
            return (f"ℹ️ {name} has no engagement data on its card yet "
                    f"(top-of-funnel prospects are not tracked).")
        visits = [int(v) for v in visits_m.group(1).replace(" ", "").split(",") if v]
        held, planned, next_call = int(held_m.group(1)), int(planned_m.group(1)), planned_m.group(2)
        png = chartpng.client_stats_png(name, visits, held, planned, next_call,
                                        role, now_iso()[:10])
        caption = (f"📈 {name} — visits {visits[0]} → {visits[-1]} over {len(visits)} weeks; "
                   f"calls held {held}, planned {planned} (next {next_call}). "
                   f"Role `{role}` · cited from the company card (broad zone).")
        return {"upload": {"filename": f"client-{name.lower().replace(' ', '-')}.png",
                           "content": png, "ctype": "image/png", "caption": caption}}

    def pipeline_chart(self, role: str) -> "dict | str":
        """`график`: the role-visible pipeline as a PNG bar chart, built from
        the SAME deal_risk envelope as the text answer — the image can never
        show more than the role may read."""
        env = self.svc.deal_risk(self.actor(role), "")
        if env.get("access") == "blocked":
            return self._blocked_message(role, env.get("title", "Deal Risk"))
        rows: list[tuple[str, int, int]] = []
        for sec in env.get("sections", []):
            table = sec.get("table") or {}
            cols = table.get("columns") or []
            if "Deal" in cols and "Win %" in cols and "Value" in cols:
                i_deal, i_win, i_val = cols.index("Deal"), cols.index("Win %"), cols.index("Value")
                for r in table.get("rows", []):
                    digits_val = re.sub(r"\D", "", r[i_val])
                    digits_win = re.sub(r"\D", "", r[i_win])
                    if not digits_val or not digits_win:
                        continue
                    rows.append((r[i_deal].replace(" - Pilot", ""),
                                 int(digits_val), int(digits_win)))
        if not rows:
            return (f"🔒 Role `{role}` sees no per-deal figures to draw — this view is "
                    f"aggregated. Needs role: `account-exec` / `head-of-sales` / "
                    f"`revenue-ops` / `admin`, or `request access`.")
        png = chartpng.pipeline_chart_png(rows, role, env.get("as_of", ""))
        caption = (f"📊 Pipeline — {len(rows)} deal(s); dark = weighted (value × win%). "
                   f"Role `{role}` · built from cited deal cards.")
        return {"upload": {"filename": f"pipeline-{role}.png", "content": png,
                           "ctype": "image/png", "caption": caption}}

    def access_chart(self, role: str) -> str:
        """ASCII bar chart of how the current role's access splits across the read
        tools — reinforces the permissions story with zero dependencies."""
        actor = self.actor(role)
        probes = [
            self.svc.company_brief(actor, "BluePeak Energy"),
            self.svc.deal_risk(actor, "BluePeak Energy"),
            self.svc.call_prep(actor, "BluePeak Energy"),
            self.svc.lead_priority(actor, "BluePeak Energy"),
            self.svc.event_brief(actor, "Sales Tech Summit 2026"),
            self.svc.campaign_brief(actor, "Q3 ROI Push"),
            self.svc.content_opportunities(actor),
            self.svc.my_day(actor),
            self.svc.pipeline_risk_digest(actor),
        ]
        counts = Counter(p.get("access", "?") for p in probes)
        order = ["allowed", "sanitized", "aggregated", "blocked", "not-found"]
        keys = [k for k in order if counts.get(k)] + [k for k in counts if k not in order]
        peak = max(counts.values())
        lines = [f"📈 Role `{role}` access across {len(probes)} tools:", "```"]
        for key in keys:
            value = counts[key]
            bar = "█" * max(1, round(value / peak * 12))
            lines.append(f"{key:11} {bar} {value}")
        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def _format_sources(citations: list[dict]) -> str | None:
        """Readable provenance for chat: card titles, not raw file paths.

        Accessible cards (with a path) become their title; restricted handles are
        already explained in the answer's "Restricted For Your Role" section, so
        they are summarised here as a count rather than a broken URL.
        """
        titles: list[str] = []
        handles: set[str] = set()
        for c in citations:
            path = c.get("path")
            if path:
                name = path.rsplit("/", 1)[-1]
                if name.endswith(".md"):
                    name = name[:-3]
                name = name.replace(" - ", " — ")
                if name not in titles:  # dedup: a card cited twice lists once
                    titles.append(name)
            elif c.get("handle"):
                handles.add(c.get("handle"))
        if not titles and not handles:
            return None
        parts = []
        if titles:  # one source per line — Rocket.Chat doesn't wrap a "·"-joined line well
            listing = "\n".join(f"   - {t}" for t in titles)
            parts.append(f"📎 Sources ({len(titles)}):\n{listing}")
        if handles:
            parts.append(f"🔒 + {len(handles)} under access on request")
        return "\n".join(parts)

    def _rewrite_sources(self, text: str, citations: list[dict]) -> str:
        """Swap the raw `**Sources:** path; path` line for readable titles."""
        clean = self._format_sources(citations)
        out = []
        for line in text.split("\n"):
            if line.startswith("**Sources:**"):
                if clean:
                    out.append(clean)
            else:
                out.append(line)
        return "\n".join(out)

    def _format_tables(self, text: str) -> tuple[str, bool]:
        """Rocket.Chat soft-wraps wide tables and breaks alignment, so re-render any
        `| ... |` table block as vertical record cards (one "field: value" block per
        row) inside a code fence — long text never wraps a column. Restricted cells
        become a 🔒 marker (explained once at the top). Returns (text, any_locked)."""
        lines = text.split("\n")
        out: list[str] = []
        any_locked = False
        i = 0
        while i < len(lines):
            if lines[i].lstrip().startswith("|"):
                block = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    block.append(lines[i])
                    i += 1
                rendered, had_lock = self._render_cards(block)
                out.append(rendered)
                any_locked = any_locked or had_lock
            else:
                out.append(lines[i])
                i += 1
        return "\n".join(out), any_locked

    @staticmethod
    def _strip_restricted_sections(text: str) -> tuple[str, bool]:
        """Drop the verbose '## Restricted For Your Role' blocks — the single
        top-of-report notice covers them. Returns (text, found_any)."""
        lines = text.split("\n")
        out: list[str] = []
        found = False
        i = 0
        while i < len(lines):
            if lines[i].strip().lower() == "## restricted for your role":
                found = True
                i += 1
                while i < len(lines) and (lines[i].startswith("- ") or lines[i].strip() == ""):
                    i += 1
                continue
            out.append(lines[i])
            i += 1
        return "\n".join(out), found

    @staticmethod
    def _render_cards(block: list[str]) -> tuple[str, bool]:
        had_na = False
        rows: list[list[str]] = []
        for line in block:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and all(c and set(c) <= set("-: ") for c in cells):
                continue  # separator row
            cleaned = []
            for cell in cells:
                if cell.rstrip(".").lower() == "restricted for your role":
                    cleaned.append("🔒")
                    had_na = True
                else:
                    cleaned.append(cell)
            rows.append(cleaned)
        if len(rows) < 2:
            return "\n".join(block), had_na
        headers, data = rows[0], rows[1:]
        cards: list[str] = []
        for row in data:
            row = row + [""] * (len(headers) - len(row))
            title, start = row[0], 1
            # A short second column (e.g. a score band) reads well on the title line.
            if len(row) > 1 and row[1] and len(row[1]) <= 14 and " " not in row[1]:
                title, start = f"{row[0]} · {row[1]}", 2
            labels = [headers[c] for c in range(start, len(headers)) if row[c]]
            width = max((len(lbl) for lbl in labels), default=0)
            lines = [title]
            for c in range(start, len(headers)):
                if row[c]:
                    lines.append(f"  {(headers[c] + ':').ljust(width + 1)} {row[c]}")
            cards.append("\n".join(lines))
        return "```\n" + "\n\n".join(cards) + "\n```", had_na

    @staticmethod
    def _blocked_message(role: str, title: str) -> str:
        """A hard 'no access' answer, naming the roles that would unlock it."""
        hint = _unlock_hint(_missing_boundaries(role)) or "a role with broader access"
        return (
            f"🤖 **SalesWiki** · role `{role}`\n\n"
            f"🔒 Role `{role}` has no access to this data (*{title}*).\n"
            f"Needs role: {hint}. Or `request access` (a curator/admin approves the request)."
        )

    @staticmethod
    def _access_notice(role: str, abac_masked: bool = False) -> str:
        """One top-of-answer notice explaining what is withheld and which role
        unlocks it.

        - `abac_masked` (a 🔒 inside a table) means a specific record is hidden by
          ownership/team, not by boundary tier — name the cross-team roles, never
          claim 'only personal-data'.
        - Otherwise the withholding is boundary-level: a role that already has
          commercial access and is only missing personal-data sees a soft
          'by request' note; a top-tier role (nothing higher) sees a neutral note;
          everyone else is told exactly which role unlocks each boundary."""
        if abac_masked:
            return (
                f"\n\n🔒 Some rows are hidden — access is by deal owner/team. "
                f"Full view for `head-of-sales` / `curator` / `admin`, or `request access`."
            )
        missing = _missing_boundaries(role)
        if not missing:
            return (
                f"\n\nℹ️ Some data is available only by separate request/approval "
                f"(audited) — `request access`."
            )
        if missing == ["personal-data"]:
            roles = " / ".join(f"`{r}`" for r in BOUNDARY_UNLOCK_ROLES["personal-data"])
            return (
                f"\n\nℹ️ You have commercial access. Only personal data (personal-data) "
                f"is withheld — available on request: role {roles}, or `request access`."
            )
        return (
            f"\n\n🔒 Some data is hidden for role `{role}` — marked 🔒. "
            f"Needs role: {_unlock_hint(missing)}. Or `request access`."
        )

    @staticmethod
    def _table_headline(lines: list[str]) -> str:
        """Pull the single most salient row from a rendered markdown table: the
        top Value (money) or Score. Grounded — reads only cited cell values."""
        num = lambda v: (float(re.search(r"[\d.]+", str(v).replace(",", "")).group())
                         if re.search(r"[\d.]+", str(v).replace(",", "")) else -1.0)
        i = 0
        while i < len(lines):
            if lines[i].lstrip().startswith("|"):
                block = []
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    block.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                    i += 1
                if len(block) < 3:
                    continue
                cols, rows = block[0], block[2:]  # [1] is the --- separator
                for key, label in (("Value", "highest value"), ("Score", "top by score")):
                    if key in cols:
                        idx = cols.index(key)
                        ranked = [r for r in rows if idx < len(r) and num(r[idx]) >= 0]
                        if ranked:
                            top = max(ranked, key=lambda r: num(r[idx]))
                            return f"{label} — {top[0]} ({top[idx]})"
            else:
                i += 1
        return ""

    def _compose_summary(self, env: dict) -> str:
        """A: deterministic summary built strictly from the cited envelope —
        the conclusion plus the top table row. No generation, no new facts."""
        lines = env.get("text", "").split("\n")
        conclusion = next((l.split("**Conclusion:**", 1)[1].strip()
                           for l in lines if l.startswith("**Conclusion:**")), "")
        headline = self._table_headline(lines)
        bits = [b for b in (conclusion, headline) if b]
        return "; ".join(bits)

    def _llm_summary(self, env: dict) -> str | None:
        """B (opt-in): a real LLM rephrases the cited envelope. Off unless
        RC_LLM_SUMMARY is set and an API key is present; any failure falls back
        to the deterministic composer so the demo never breaks. Grounding rule:
        the prompt forbids any fact not present in the envelope text."""
        if not self.feature_enabled("llm_summary", "RC_LLM_SUMMARY"):
            return None
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return None
        try:
            prompt = (
                "You are summarizing a sales answer for a chat user. Use ONLY facts "
                "present in the text below — invent nothing, add no numbers not shown. "
                "Reply with one or two short sentences in English.\n\n" + env.get("text", "")
            )
            return self._llm_call(prompt, 160) or None
        except Exception:
            return None  # never break the answer on a summary failure

    def _llm_call(self, prompt: str, max_tokens: int) -> str:
        """One grounded Anthropic API call, shared by the summary headline and
        the recommendations block. Raises on any transport/API failure —
        callers decide their own fallback."""
        key = os.environ["ANTHROPIC_API_KEY"].strip()
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=payload,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()

    # Digests where an LLM ranking adds value on top of the deterministic answer.
    _DIGEST_METHODS = frozenset({"my_day", "pipeline_risk_digest", "deal_risk"})

    def _llm_recommendations(self, env: dict, method: str) -> str:
        """Opt-in (RC_LLM_RECS=1 + ANTHROPIC_API_KEY): an LLM turns a digest
        envelope into a prioritized what-first action list. Grounding rule: the
        prompt gets only the envelope text and forbids new facts; the block is
        explicitly labeled as generated. Digest-only; any failure returns "" so
        the deterministic answer always stands on its own."""
        if method not in self._DIGEST_METHODS:
            return ""
        if env.get("access") in ("blocked", "not-found", "ambiguous"):
            return ""
        if not self.feature_enabled("llm_recommendations", "RC_LLM_RECS"):
            return ""
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            return ""
        try:
            prompt = (
                "You are a sales assistant. Using ONLY the facts in the digest below "
                "— invent nothing, add no numbers, names or dates not shown — rank "
                "the items by urgency and reply with a short numbered action list "
                "for today (max 5 items, one line each, most urgent first, each "
                "with a one-clause reason). Plain numbered lines only — no "
                "headings, no bold, no preamble.\n\n" + env.get("text", "")
            )
            body = self._llm_call(prompt, 400)
        except Exception:
            return ""  # never break the answer on a recommendations failure
        return f"\n\n{RECS_MARKER}\n{body}" if body else ""

    def _summary_line(self, env: dict) -> str:
        """The '🤖 Summary' headline (real LLM if enabled, else deterministic).
        Only for substantive read answers."""
        if env.get("access") in ("blocked", "not-found", "ambiguous"):
            return ""
        body = self._llm_summary(env) or self._compose_summary(env)
        return f"{SUMMARY_MARKER} (from card data): {body}\n\n" if body else ""

    @staticmethod
    def _readable_spacing(text: str) -> str:
        """Put a blank line before the footer blocks so the answer breathes
        (Rocket.Chat renders consecutive lines cramped)."""
        markers = ("**Confidence:**", "📎 Sources", "**Next action:**",
                   "**Access:**", "📎 Need a file")
        out: list[str] = []
        for line in text.split("\n"):
            if any(line.startswith(m) for m in markers) and out and out[-1].strip():
                out.append("")
            out.append(line)
        return "\n".join(out)

    @staticmethod
    def _friendly_headings(body: str) -> str:
        """Rewrite brief section headings that leak internal zone names
        (`## Broad - Lead - X`, `## Sales Confidential - Deal - X`) into plain,
        reader-friendly labels, marking confidential zones."""
        labels = {
            "lead": "Lead", "private case": "ROI case", "source": "Market signal",
            "call": "Call", "competitor intel": "Competitor", "deal": "Deal",
            "company": "Company", "personal data ref": "Personal data",
        }
        norm = lambda s: re.sub(r"[-\s]+", " ", s).strip().lower()  # hyphen/space-insensitive
        out = []
        for line in body.split("\n"):
            if line.startswith("## "):
                title = line[3:].strip()
                confidential = False
                for zone in ("Sales Confidential - ", "Personal Data - ", "Broad - "):
                    if norm(title).startswith(norm(zone) + " "):
                        confidential = not zone.startswith("Broad")
                        title = title[len(zone):]
                        break
                else:
                    out.append(line)
                    continue
                label = labels.get(norm(title.split(" - ", 1)[0]), title)
                if confidential:
                    label += " (confidential)"
                out.append(f"## {label}")
            else:
                out.append(line)
        return "\n".join(out)

    def _render(self, role: str, env: dict) -> str:
        access = env.get("access")
        header = f"🤖 **SalesWiki** · role `{role}`"
        if access == "blocked":
            return self._blocked_message(role, env.get("title", "request"))
        if access == "not-found":
            return f"{header}\n\nℹ️ {env.get('conclusion') or 'Nothing found for this request.'}"
        body = self._rewrite_sources(env.get("text", "").strip(), env.get("citations", []))
        body, stripped = self._strip_restricted_sections(body)
        body = self._friendly_headings(body)
        body, locked = self._format_tables(body)
        # One rule: explain missing permissions ONCE at the top; mark the rest with 🔒.
        restricted = locked or stripped or access in {"sanitized", "aggregated"}
        notice = self._access_notice(role, abac_masked=locked) if restricted else ""
        summary = self._summary_line(env)
        return f"{header}{notice}\n\n{summary}{self._readable_spacing(body)}"

    @staticmethod
    def company_id(name: str) -> str:
        return "demo-company-" + name.lower().replace(" ", "-")
