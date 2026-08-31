"""Card inspection, staged ingest and governance workflows for the chat bridge."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from _bridge_common import *  # noqa: F403
from _bridge_common import _child_env
from saleswiki_mcp.formatter import extract_section


class WikiWorkflowMixin:
    @staticmethod
    def detect_company(text: str) -> str | None:
        low = text.lower()
        for name in DEMO_COMPANIES:
            if name.lower() in low:
                return name
        return None

    @staticmethod
    def _read_card(path: Path) -> tuple[dict, dict, list]:
        """Parse a card into (frontmatter, sections, section_order). Frontmatter is
        the top-level `key: value` pairs; sections map `## Heading` -> body lines."""
        text = path.read_text(encoding="utf-8")
        fm: dict[str, str] = {}
        body = text
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                for line in text[3:end].splitlines():
                    if ":" in line and not line.startswith((" ", "-")):
                        key, _, value = line.partition(":")
                        fm[key.strip()] = value.strip()
                body = text[end + 4:]
        sections: dict[str, list[str]] = {}
        order: list[str] = []
        current = None
        for line in body.splitlines():
            if line.startswith("## "):
                current = line[3:].strip()
                sections[current] = []
                order.append(current)
            elif current is not None:
                sections[current].append(line)
        return fm, sections, order

    def card_xray(self, role: str, name: str) -> str:
        """Presenter 'behind the glass' reveal: everything stored about a company
        across all access zones, with the card's governance sections annotated.
        Reads raw vault files directly (not via the gateway) — a teaching surface
        that shows exactly what the gateway filters per role.

        No-leak: closed-zone card *names* (deal/person names are themselves the
        secret) are listed only for a role that may read that boundary. A role
        without access still learns the zone exists, how many cards it holds and
        which role unlocks it — never the stems."""
        root = self.vault_root
        md_files = [p for p in root.rglob("*.md") if name.lower() in p.name.lower()]
        if not md_files:
            return (f"🤔 No cards found for \"{name}\" in the demo vault. "
                    f"Companies: {', '.join(DEMO_COMPANIES)}.")
        by_boundary: dict[str, list[Path]] = {}
        for p in md_files:
            boundary = p.relative_to(root).parts[0]
            by_boundary.setdefault(boundary, []).append(p)

        lines = [
            f"🎬 **BEHIND THE GLASS — what is actually stored about \"{name}\"**",
            "_This is the source-of-truth markdown. The gateway derives each role's answer "
            "from here, cutting the closed zones._",
            "",
        ]
        company_card = next((p for p in md_files if p.name.startswith("Company -")), None)
        if company_card:
            fm, sections, order = self._read_card(company_card)
            gov = " · ".join(f"`{k}: {fm[k]}`"
                             for k in ("access", "boundary", "profile_lock", "freshness")
                             if k in fm)
            if gov:
                lines += [f"**Governance fields:** {gov}",
                          "↳ the gateway uses these to decide what to show a role.", ""]
            lines.append("**Card zones:**")
            for heading, (emoji, explain) in XRAY_ZONES.items():
                if heading in sections:
                    lines.append(f"{emoji} **{heading}** — {explain}")
                    for body_line in [l for l in sections[heading] if l.strip()][:4]:
                        lines.append(f"    {body_line.strip()}")
            others = [h for h in order if h not in XRAY_ZONES]
            if others:
                lines.append(f"✏️ _other working sections:_ {', '.join(others)}")
            lines.append("")

        closed = {b: ps for b, ps in by_boundary.items() if b != "broad"}
        if closed:
            # Gate the per-card reveal on the gateway's real read decision (RBAC
            # boundary AND ABAC ownership AND live grants), not just boundary
            # membership: an ownership-constrained role (SDR/AE) must not see
            # another team's card stems, matching what the gateway would answer.
            readable = self.svc.readable_card_paths(self.actor(role))
            lines.append(f"**What else is stored about \"{name}\" "
                         f"(closed zones — only for roles with access):**")
            for boundary, paths in sorted(closed.items()):
                audience = BOUNDARY_AUDIENCE.get(boundary, "limited access")
                visible = [p for p in sorted(paths) if p.relative_to(root).as_posix() in readable]
                if visible:
                    lines.append(f"📂 _{boundary}_ — {audience}:")
                    for p in visible:
                        lines.append(f"    - {p.stem}")
                    hidden = len(paths) - len(visible)
                    if hidden:
                        lines.append(f"    …and {hidden} more not readable by `{role}` for this account.")
                else:
                    # No-leak: count + who unlocks it, but never the card names.
                    unlock = " / ".join(f"`{r}`" for r in BOUNDARY_UNLOCK_ROLES.get(boundary, [])) or audience
                    lines.append(f"📂 _{boundary}_ — {len(paths)} card(s), hidden from `{role}` "
                                 f"({audience}); switch role to {unlock} to reveal.")
            lines.append("")
        lines.append("_Open the same file in Obsidian — it is literally the source of truth. "
                     "How cards are born and change — command `how it works`._")
        return "\n".join(lines)

    # -- Google Drive connector (synthetic; no OAuth/network) --------------
    def _drive_manifest(self) -> dict:
        """Read the synthetic Drive manifest written into the demo vault, or {}."""
        path = self.vault_root / "connectors" / "gdrive-manifest.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _role_sees_boundary(role: str, boundary: str) -> bool:
        return boundary in ROLE_BOUNDARIES.get(role, {"broad"})

    @staticmethod
    def _new_count(files: list[dict]) -> int:
        return sum(1 for f in files if f.get("status") == "new")

    def drive_folders(self, role: str) -> str:
        """List connected folders + a new-resource count. Folders the role cannot
        see are shown as locked (name only), never their contents."""
        manifest = self._drive_manifest()
        folders = manifest.get("folders", {})
        if not folders:
            return "📁 Google Drive is not connected in this demo vault (no connector manifest)."
        lines = ["📁 **Google Drive connected** (demo, read-only). Folders:"]
        for name, meta in folders.items():
            boundary = meta.get("boundary", "broad")
            if self._role_sees_boundary(role, boundary):
                files = meta.get("files", [])
                new = self._new_count(files)
                tail = f"(🆕 {new} new)" if new else "(no new)"
                lines.append(f"   - `{name}` — {len(files)} file(s) {tail}")
            else:
                lines.append(f"   - `{name}` — 🔒 restricted for role `{role}` ({boundary})")
        lines.append("Open a folder: `drive Sales/Q3-Calls`. Process all new: `process all`.")
        return "\n".join(lines)

    def drive_folder(self, role: str, folder: str) -> str:
        """List resources in one folder, gated by role (no-leak), answering the
        yes/no-resources question and offering to process the new ones."""
        manifest = self._drive_manifest()
        meta = manifest.get("folders", {}).get(folder)
        if meta is None:
            known = ", ".join(manifest.get("folders", {}).keys()) or "—"
            return f"🤔 Folder `{folder}` is not connected. Available: {known}."
        boundary = meta.get("boundary", "broad")
        if not self._role_sees_boundary(role, boundary):
            return (f"🔒 Folder `{folder}` is in zone `{boundary}` — not available to role `{role}`. "
                    f"Switch role (`role: account-exec` / `role: curator`) or `request access`.")
        files = meta.get("files", [])
        new = self._new_count(files)
        verdict = f"yes, resources found ({len(files)}; 🆕 {new} new)" if new else \
                  f"resources present ({len(files)}), none new"
        lines = [f"📁 `{folder}` — {verdict}:"]
        for f in files:
            mark = "🆕" if f.get("status") == "new" else "✅"
            tail = "" if f.get("status") == "new" else " (already processed)"
            lines.append(f"   {mark} `{f['id']}` · {f.get('kind', '')} · "
                         f"{f.get('name', '')} → `{f.get('maps_to', '')}`{tail}")
        if new:
            lines.append("Process: `process <id>` (e.g. `process "
                         f"{next(f['id'] for f in files if f.get('status') == 'new')}`) "
                         "or `process all`.")
        return "\n".join(lines)

    def _find_drive_file(self, file_id: str) -> tuple[str | None, dict | None]:
        """Locate a file by id across folders; returns (folder, file) or (None, None)."""
        for folder, meta in self._drive_manifest().get("folders", {}).items():
            for f in meta.get("files", []):
                if f.get("id") == file_id:
                    return folder, f
        return None, None

    def _ingest_note(self, f: dict) -> str:
        return (f"Drive {f['id']}: {f.get('name', '')} ({f.get('kind', '')}) — "
                f"create/update card from source [synthetic]")

    def propose_ingest(self, role: str, target_id: str, note: str) -> str:
        """File an `ingest_resource` proposal (in-process: the manifest is local to
        the demo). Returns the proposal id."""
        return self.svc.ingest_resource(self.actor(role), target_id, note)

    def drive_process(self, role: str, spec: str) -> str:
        """Turn 'process <id>' or 'process all' into ingest proposals, respecting
        folder visibility (a file in a closed folder cannot be processed)."""
        manifest = self._drive_manifest()
        if spec in ("всё", "все", "all", "*"):
            created = []
            for folder, meta in manifest.get("folders", {}).items():
                if not self._role_sees_boundary(role, meta.get("boundary", "broad")):
                    continue
                for f in meta.get("files", []):
                    if f.get("status") == "new":
                        pid = self.propose_ingest(role, f.get("maps_to", ""), self._ingest_note(f))
                        created.append((pid, f))
            if not created:
                return "No new resources to process in the folders available to you."
            lines = [f"📥 Ingest proposals created: {len(created)}."]
            for pid, f in created:
                lines.append(f"   - `{pid}` ← {f['id']} ({f.get('name', '')})")
            lines.append("🔔 For curators: `review queue` → `approve <id>` → `apply`.")
            return "\n".join(lines)

        folder, f = self._find_drive_file(spec)
        if f is None:
            return (f"🤔 File `{spec}` not found on the connected Drive. "
                    f"Look here: `drive <folder>`.")
        meta = manifest["folders"][folder]
        if not self._role_sees_boundary(role, meta.get("boundary", "broad")):
            return (f"🔒 File `{spec}` is in the closed zone `{meta.get('boundary')}` — "
                    f"role `{role}` cannot process it. Switch role or `request access`.")
        if f.get("status") != "new":
            return f"✅ `{spec}` was already processed earlier — no new proposal needed."
        pid = self.propose_ingest(role, f.get("maps_to", ""), self._ingest_note(f))
        return (f"📥 Ingest proposed: `{pid}` ({f['id']} → {f.get('maps_to', '')}).\n"
                f"The card itself is not changed — the edit appears in Review Needed after apply.\n"
                f"🔔 For curators: `review queue` → `approve {pid}` → `apply`.")

    def request_access(self, role: str, target_id: str, reason: str) -> str:
        """Returns the proposal id (in MCP mode, parsed from the MCP tool reply)."""
        return self._propose(role, "request_access", target_id, "reason", reason)

    def flag_stale(self, role: str, target_id: str, note: str) -> str:
        """File a `flag_stale_or_wrong` proposal; returns the proposal id."""
        return self._propose(role, "flag_stale_or_wrong", target_id, "note", note)

    def request_redaction(self, role: str, target_id: str, reason: str) -> str:
        """File a `request_redaction_review` proposal; returns the proposal id."""
        return self._propose(role, "request_redaction_review", target_id, "reason", reason)

    def _propose(self, role: str, tool: str, target_id: str, note_key: str, note: str) -> str:
        """Capture any propose-type proposal (access / flag / redaction) through the
        same path, in-process or via the MCP server, and return the proposal id."""
        if self.use_mcp:
            _text, data = asyncio.run(self._mcp_call(
                ROLES[role][0], f"saleswiki.{tool}", {"target": target_id, note_key: note}))
            return str(data.get("proposal_id", "proposal-?"))
        return getattr(self.svc, tool)(self.actor(role), target_id, note)

    def review_queue(self, role: str) -> str:
        if self.use_mcp:
            text, data = asyncio.run(self._mcp_call(ROLES[role][0], "saleswiki.review_queue", {}))
            if data.get("access") != "allowed":  # same envelope gate as in-process
                return (
                    f"🔒 The review queue is visible only to reviewer roles (e.g. `curator`, `admin`). "
                    f"Role `{role}` has no access — switch role: `role: curator`."
                )
            return f"🤖 **SalesWiki** · role `{role}` · via MCP\n\n{text.strip()}"
        env = self.svc.review_queue(self.actor(role))
        if env.get("access") != "allowed":
            return (
                f"🔒 The review queue is visible only to reviewer roles (e.g. `curator`, `admin`). "
                f"Role `{role}` has no access — switch role: `role: curator`."
            )
        return f"🤖 **SalesWiki** · role `{role}`\n\n{env.get('text', '').strip()}"

    def pending_count(self, role: str) -> int:
        """How many proposals still await a decision (draft only), 0 if the role
        cannot review — used for the reviewer notification."""
        env = self.svc.review_queue(self.actor(role))
        if env.get("access") != "allowed":
            return 0
        return sum(1 for i in env.get("items", []) if i.get("status") == "draft")

    def decide(self, role: str, action: str, pid: str, reason: str = "", ttl_days: int | None = None) -> str:
        """Approve / reject / revoke a proposal (approver roles only). Approving a
        request_access issues a live scoped grant; revoking drops it."""
        # Read the proposal type up front (via the public service API, which reads
        # the shared proposals.jsonl that MCP spawns also write) so the approval
        # reply matches what approval means in BOTH backends: only request_access
        # grants data; flag/redaction just queue a fix.
        ptype = self.svc.proposal_state(pid).get("type", "") if action == "approve" else ""
        if self.use_mcp:
            tool = {"approve": "saleswiki.approve_proposal", "reject": "saleswiki.reject_proposal",
                    "revoke": "saleswiki.revoke_proposal"}[action]
            args: dict = {"proposal_id": pid}
            if action == "approve" and ttl_days is not None:
                args["ttl_days"] = ttl_days  # the approver's TTL rides through MCP too
            if action in ("reject", "revoke"):
                args["reason"] = reason or "no reason given"
            # The envelope carries the same service-result shape the in-process
            # branch gets, so both modes share one rendering path below — no
            # keyword-sniffing of the rendered reply.
            _reply, data = asyncio.run(self._mcp_call(ROLES[role][0], tool, args))
            res = {**data, "type": ptype}
        else:
            actor = self.actor(role)
            if action == "approve":
                res = self.svc.approve_proposal(actor, pid, ttl_days=ttl_days)
                res["type"] = ptype
            elif action == "revoke":
                res = self.svc.revoke_proposal(actor, pid, reason or "no reason given")
            else:
                res = self.svc.reject_proposal(actor, pid, reason or "no reason given")
        status = res.get("status")
        pid = res.get("proposal_id", pid)
        # No-op re-decision: the proposal was decided earlier. Say so honestly —
        # never report a fresh grant/decision that was not issued. The service
        # signals it with reason 'not in draft' (approve/reject) or 'not an
        # active grant' (revoke) while echoing the CURRENT status, identically
        # in-process and over MCP (the envelope carries the same fields).
        if res.get("reason") in ("not in draft", "not an active grant"):
            prior = status or "decided"
            return (f"ℹ️ Request `{pid}` was already {prior} — nothing changed and "
                    f"no new grant was issued.")
        if status == "approved":
            ptype = res.get("type", "")
            if ptype in ("flag_stale_or_wrong", "request_redaction_review", "ingest_resource"):
                what = {"flag_stale_or_wrong": "data fix",
                        "request_redaction_review": "personal-data redaction",
                        "ingest_resource": "resource ingest"}[ptype]
                return (
                    f"✅ Request `{pid}` approved by role `{role}` ({what}). "
                    f"The change was handed to the Review Needed section — the single-writer worker applies it. "
                    f"This does NOT grant data access."
                )
            window = f"{ttl_days} days" if ttl_days else "30 days (default)"
            return (
                f"✅ Request `{pid}` approved by role `{role}`. Access granted for {window} — "
                f"the requester now sees this company's data (same role, no switch). "
                f"Revoke early: `revoke {pid} <reason>`."
            )
        if status == "revoked":
            return f"♻️ Grant for request `{pid}` revoked by role `{role}`. The requester is without access again."
        if status == "rejected":
            # A fresh reject result carries no reason field; show the approver's
            # typed reason (identically in-process and over MCP).
            return f"🚫 Request `{pid}` rejected. Reason: {res.get('reason') or reason or '—'}"
        if status == "blocked":
            return (
                f"🔒 Role `{role}` cannot decide on requests — needs `curator`/`hos`/`admin`. "
                f"Switch role: `role: curator`."
            )
        if status == "not-found":
            return f"❓ Request `{pid}` not found. Check the id via `review queue`."
        return f"ℹ️ Request `{pid}`: {status} ({res.get('reason', '')})."

    def _is_reviewer(self, role: str) -> bool:
        """A role that may see the review queue may also trigger the worker."""
        return self.svc.review_queue(self.actor(role)).get("access") == "allowed"

    def _review_needed_tail(self, base_path: str) -> str:
        """The last Review Needed bullet of a card (the just-applied note), or ''."""
        if not base_path:
            return ""
        try:
            body = (self.vault_root / base_path).read_text(encoding="utf-8")
        except OSError:
            return ""
        bullets = [ln.strip().lstrip("-").strip()
                   for ln in extract_section(body, "Review Needed").splitlines() if ln.strip()]
        return bullets[-1] if bullets else ""

    def apply_proposals(self, role: str) -> str:
        """Run the single-writer worker as a SEPARATE process to apply approved
        proposals to their cards' Review Needed section. The gateway never imports
        the worker; spawning it mirrors the real single-writer deployment (same
        pattern as RC_USE_MCP spawning the MCP server)."""
        if not self._is_reviewer(role):
            return (
                f"🔒 Approved requests can be applied only by reviewer roles "
                f"(`curator`/`head-of-sales`/`revenue-ops`/`admin`). Role `{role}` has no rights."
            )
        before = {pid for pid, s in self.svc.proposal_states().items() if s.get("status") == "applied"}
        env = _child_env(
            SALESWIKI_VAULT_ROOT=str(self.vault_root),
            SALESWIKI_RUNTIME_DIR=str(self.runtime),
            PYTHONPATH=str(ROOT),
        )
        try:
            subprocess.run([sys.executable, "-m", "saleswiki_mcp.worker"],
                           cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=30, check=False)
        except (subprocess.SubprocessError, OSError) as exc:
            return f"⚠️ Could not start the worker: {exc}"
        applied = sorted(
            (pid, s) for pid, s in self.svc.proposal_states().items()
            if s.get("status") == "applied" and pid not in before
        )
        if not applied:
            return "ℹ️ No approved requests to apply (or already applied). First `approve <id>`."
        lines = [f"🔧 Single-writer worker applied {len(applied)} change(s) to the *Review Needed* section:", ""]
        for pid, s in applied:
            lines.append(f"- `{pid}` ({s.get('type', '')}) → {s.get('target', '')}: {s.get('note', '')}")
            tail = self._review_needed_tail(s.get("base_path", ""))
            if tail:
                lines.append(f"    📝 in card: {tail}")
            lines.append("")
        return "\n".join(lines).rstrip()
