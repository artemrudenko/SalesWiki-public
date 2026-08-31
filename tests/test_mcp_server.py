"""Phase 4 tests: MCP server tool wiring over the permissioned core.

Every tool handler returns the full envelope dict — rendered Markdown under
"text" plus machine-readable semantics (access / status / reason /
proposal_id) — so the MCP layer can send the text as content and the rest as
structuredContent, so clients never re-parse semantics out of prose. The pure
handlers are tested without the SDK transport; the FastMCP
wiring is exercised only when the `mcp` package is importable (skipped
otherwise so the suite still runs under a plain interpreter).
Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config, server  # noqa: E402
from saleswiki_mcp.identity import FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.service import build_default_service  # noqa: E402

MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None
SALES_SECRETS = ("Discount floor", "Pricing:", "ACV")


def _runtime(actor_id: str):
    tmp = Path(tempfile.mkdtemp(prefix="mcp-"))
    vault = tmp / "permissioned"
    gdv.generate_permissioned_demo(vault)
    svc = build_default_service(vault, tmp / "audit.jsonl", tmp / "proposals.jsonl", now=lambda: "t")
    actor = FixtureIdentityProvider(actor_id, config.identity_config()).resolve()
    return tmp, svc, server.build_tools(svc, actor)


class ToolHandlers(unittest.TestCase):
    def test_tool_names(self) -> None:
        _, _, tools = _runtime("demo-ivan-ae")
        self.assertIn("saleswiki.company_brief", tools)
        self.assertIn("saleswiki.company_search", tools)
        self.assertIn("saleswiki.entity_graph", tools)
        self.assertIn("saleswiki.flag_stale_or_wrong", tools)
        self.assertIn("saleswiki.deal_risk", tools)
        self.assertIn("saleswiki.call_prep", tools)
        self.assertIn("saleswiki.lead_priority", tools)
        self.assertIn("saleswiki.event_brief", tools)
        self.assertIn("saleswiki.approve_proposal", tools)
        self.assertIn("saleswiki.request_redaction_review", tools)
        self.assertIn("saleswiki.ingest_resource", tools)
        self.assertIn("saleswiki.my_day", tools)
        self.assertIn("saleswiki.pipeline_risk_digest", tools)
        self.assertIn("saleswiki.campaign_brief", tools)
        self.assertIn("saleswiki.content_opportunities", tools)
        self.assertIn("saleswiki.review_queue", tools)
        self.assertIn("saleswiki.get_proposal", tools)
        self.assertIn("saleswiki.reject_proposal", tools)

    def test_governance_inbox_is_role_gated(self) -> None:
        tmp, svc, curator = _runtime("demo-marina-curator")
        pid = svc.flag_stale_or_wrong(
            FixtureIdentityProvider("demo-ivan-ae", config.identity_config()).resolve(),
            "demo-company-bluepeak-energy", "stale",
        )
        _, _, mkt = _runtime("demo-nina-marketing")
        self.assertIn("Review Queue", curator["saleswiki.review_queue"]("")["text"])
        self.assertIn("Blocked", mkt["saleswiki.review_queue"]("")["text"])
        self.assertIn("rejected", curator["saleswiki.reject_proposal"](pid, "no")["text"].lower())

    def test_marketing_workbench_tools(self) -> None:
        _, _, owner = _runtime("demo-ivan-ae")
        _, _, mkt = _runtime("demo-nina-marketing")
        self.assertIn("Energy cost volatility", mkt["saleswiki.content_opportunities"]("")["text"])
        self.assertIn("economic buyer", owner["saleswiki.campaign_brief"]("Q3 ROI Push")["text"])
        self.assertNotIn("economic buyer", mkt["saleswiki.campaign_brief"]("Q3 ROI Push")["text"])

    def test_my_day_and_pipeline_digest_are_role_shaped(self) -> None:
        _, _, owner = _runtime("demo-ivan-ae")
        _, _, mkt = _runtime("demo-nina-marketing")
        self.assertIn("economic buyer", owner["saleswiki.my_day"]("")["text"])
        self.assertNotIn("economic buyer", mkt["saleswiki.my_day"]("")["text"])
        _, _, hos = _runtime("demo-elena-hos")
        digest = hos["saleswiki.pipeline_risk_digest"]("")["text"]
        self.assertIn("Pipeline Risk Digest", digest)
        self.assertIn("Northstar Robotics", digest)

    def test_request_redaction_review_captures_proposal(self) -> None:
        tmp, _, tools = _runtime("demo-nina-marketing")
        out = tools["saleswiki.request_redaction_review"]("demo-company-bluepeak-energy", "contact PII exposed")
        self.assertIn("proposal-", out["text"])
        records = [json.loads(l) for l in (tmp / "proposals.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual(records[0]["type"], "request_redaction_review")
        self.assertEqual(records[0]["status"], "draft")

    def test_import_summary_is_captured_as_a_governed_draft(self) -> None:
        tmp, _, tools = _runtime("demo-ivan-ae")
        out = tools["saleswiki.ingest_resource"]("demo-company-bluepeak-energy", "company: BluePeak; next-step: review")
        self.assertEqual(out["status"], "draft")
        records = [json.loads(line) for line in (tmp / "proposals.jsonl").read_text().splitlines() if line.strip()]
        self.assertEqual(records[0]["type"], "ingest_resource")
        self.assertEqual(records[0]["note"], "company: BluePeak; next-step: review")

    def test_approve_proposal_is_role_gated(self) -> None:
        tmp, svc, curator_tools = _runtime("demo-marina-curator")
        pid = svc.flag_stale_or_wrong(
            FixtureIdentityProvider("demo-ivan-ae", config.identity_config()).resolve(),
            "demo-company-bluepeak-energy",
            "stale pricing",
        )
        _, _, sales_tools = _runtime("demo-ivan-ae")
        denied = sales_tools["saleswiki.approve_proposal"](pid)
        self.assertIn("not", denied["text"].lower())
        self.assertEqual(denied["status"], "blocked")
        ok = curator_tools["saleswiki.approve_proposal"](pid)
        self.assertIn("approved", ok["text"].lower())

    @staticmethod
    def _ttl_runtime():
        """Service with a real ISO clock (grant expiry math needs parseable now)."""
        tmp = Path(tempfile.mkdtemp(prefix="mcp-ttl-"))
        vault = tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        svc = build_default_service(
            vault, tmp / "audit.jsonl", tmp / "proposals.jsonl",
            now=lambda: "2026-06-14T00:00:00Z",
        )
        viewer = FixtureIdentityProvider("demo-broad-viewer", config.identity_config()).resolve()
        curator = FixtureIdentityProvider("demo-marina-curator", config.identity_config()).resolve()
        pid = svc.request_access(viewer, "demo-company-bluepeak-energy", "need deal risk")
        return svc, server.build_tools(svc, curator), pid

    def test_approve_proposal_accepts_ttl_days(self) -> None:
        # The approver's TTL must reach the grant; it silently became 30 days.
        svc, tools, pid = self._ttl_runtime()
        out = tools["saleswiki.approve_proposal"](pid, 7)
        self.assertIn("approved", out["text"].lower())
        self.assertEqual(svc.proposal_state(pid).get("grant_expires"), "2026-06-21T00:00:00Z")

    def test_approve_proposal_defaults_ttl_when_omitted(self) -> None:
        svc, tools, pid = self._ttl_runtime()
        tools["saleswiki.approve_proposal"](pid)
        self.assertEqual(svc.proposal_state(pid).get("grant_expires"), "2026-07-14T00:00:00Z")

    def test_approve_proposal_rejects_invalid_ttl(self) -> None:
        svc, tools, pid = self._ttl_runtime()
        out = tools["saleswiki.approve_proposal"](pid, 0)
        self.assertIn("ttl_days", out["text"])
        self.assertEqual(svc.proposal_state(pid).get("status"), "draft", "invalid ttl must not approve")

    def test_reapprove_reply_is_a_distinct_noop(self) -> None:
        # The no-op reply must carry an unambiguous marker so a client cannot
        # misread 'already approved' as a fresh approval/grant.
        _, tools, pid = self._ttl_runtime()
        tools["saleswiki.approve_proposal"](pid, 7)
        second = tools["saleswiki.approve_proposal"](pid, 7)
        self.assertIn("already in status 'approved'", second["text"])
        self.assertIn("no new grant", second["text"].lower())
        self.assertNotIn("worker will apply", second["text"])

    def test_lead_priority_is_role_shaped(self) -> None:
        _, _, owner_tools = _runtime("demo-ivan-ae")
        _, _, mkt_tools = _runtime("demo-nina-marketing")
        owner_text = owner_tools["saleswiki.lead_priority"]("")["text"]
        mkt_text = mkt_tools["saleswiki.lead_priority"]("")["text"]
        self.assertIn("BluePeak Energy", owner_text)
        self.assertIn("BluePeak Energy", mkt_text)
        self.assertIn("economic buyer", owner_text, "owner sees linked deal risk")
        self.assertNotIn("economic buyer", mkt_text, "marketing gets no linked deal detail")

    def test_event_brief_is_role_shaped(self) -> None:
        _, _, owner_tools = _runtime("demo-ivan-ae")
        _, _, mkt_tools = _runtime("demo-nina-marketing")
        owner_text = owner_tools["saleswiki.event_brief"]("Sales Tech Summit 2026")["text"]
        mkt_text = mkt_tools["saleswiki.event_brief"]("Sales Tech Summit 2026")["text"]
        for name in ("BluePeak Energy", "Northstar Robotics", "Atlas Foods"):
            self.assertIn(name, owner_text)
            self.assertIn(name, mkt_text)
        self.assertIn("economic buyer", owner_text)
        self.assertNotIn("economic buyer", mkt_text)

    def test_deal_risk_is_role_shaped(self) -> None:
        _, _, hos_tools = _runtime("demo-elena-hos")
        _, _, mkt_tools = _runtime("demo-nina-marketing")
        hos_text = hos_tools["saleswiki.deal_risk"]("")["text"]
        mkt_text = mkt_tools["saleswiki.deal_risk"]("")["text"]
        self.assertIn("Northstar Robotics", hos_text, "HoS sees all named deals")
        self.assertNotIn("Northstar Robotics", mkt_text, "marketing gets no named deals")

    def test_call_prep_is_role_shaped(self) -> None:
        _, _, owner_tools = _runtime("demo-ivan-ae")
        _, _, mkt_tools = _runtime("demo-nina-marketing")
        owner_text = owner_tools["saleswiki.call_prep"]("BluePeak Energy")["text"]
        mkt_text = mkt_tools["saleswiki.call_prep"]("BluePeak Energy")["text"]
        self.assertIn("Sanitized takeaway", owner_text)
        self.assertNotIn("Sanitized takeaway", mkt_text)
        for secret in ("internal budget", "RivalCorp"):
            self.assertNotIn(secret, owner_text)
            self.assertNotIn(secret, mkt_text)

    def test_company_brief_is_role_shaped(self) -> None:
        _, _, owner_tools = _runtime("demo-ivan-ae")
        _, _, mkt_tools = _runtime("demo-nina-marketing")
        owner_text = owner_tools["saleswiki.company_brief"]("BluePeak Energy")["text"]
        mkt_text = mkt_tools["saleswiki.company_brief"]("BluePeak Energy")["text"]
        self.assertTrue(any(s in owner_text for s in SALES_SECRETS))
        for secret in SALES_SECRETS:
            self.assertNotIn(secret, mkt_text)

    def test_entity_graph_handler_returns_graph_view(self) -> None:
        _, _, owner_tools = _runtime("demo-ivan-ae")
        graph = owner_tools["saleswiki.entity_graph"]("BluePeak Energy")
        self.assertEqual(graph["contract"], "saleswiki.graph-view")
        self.assertEqual(graph["version"], 1)
        self.assertEqual(graph["root_id"], "demo-company-bluepeak-energy")
        self.assertIn("BluePeak", graph["text"])

    def test_flag_is_append_only(self) -> None:
        tmp, _, tools = _runtime("demo-ivan-ae")
        before = {p: p.read_bytes() for p in (tmp / "permissioned").rglob("*.md")}
        out = tools["saleswiki.flag_stale_or_wrong"]("demo-company-bluepeak-energy", "stale pricing")
        self.assertIn("proposal-", out["text"])
        records = [json.loads(l) for l in (tmp / "proposals.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual(len(records), 1)
        for p, h in before.items():
            self.assertEqual(p.read_bytes(), h, "flag must not mutate production")


class StructuredEnvelopes(unittest.TestCase):
    """The handlers' envelopes carry decision/access semantics as data, so an
    MCP client never keyword-sniffs the rendered prose and a server wording
    change cannot flip a decision."""

    def test_read_envelope_carries_access_and_text(self) -> None:
        _, _, tools = _runtime("demo-ivan-ae")
        env = tools["saleswiki.company_brief"]("BluePeak Energy")
        self.assertIn("BluePeak", env["text"])
        self.assertIn("access", env)

    def test_review_queue_envelope_is_machine_readable(self) -> None:
        _, _, curator = _runtime("demo-marina-curator")
        _, _, mkt = _runtime("demo-nina-marketing")
        self.assertEqual(curator["saleswiki.review_queue"]("")["access"], "allowed")
        blocked = mkt["saleswiki.review_queue"]("")
        self.assertEqual(blocked["access"], "blocked")
        self.assertIn("Blocked", blocked["text"])

    def test_propose_envelope_carries_proposal_id(self) -> None:
        _, _, tools = _runtime("demo-ivan-ae")
        env = tools["saleswiki.flag_stale_or_wrong"]("demo-company-bluepeak-energy", "stale")
        self.assertEqual(env["status"], "draft")
        self.assertRegex(env["proposal_id"], r"^proposal-\d+$")
        self.assertIn(env["proposal_id"], env["text"])

    def test_approve_envelope_signals_fresh_vs_noop(self) -> None:
        _, tools, pid = ToolHandlers._ttl_runtime()
        fresh = tools["saleswiki.approve_proposal"](pid, 7)
        self.assertEqual(fresh["status"], "approved")
        self.assertEqual(fresh["proposal_id"], pid)
        self.assertNotIn("reason", fresh, "a fresh approval carries no no-op marker")
        noop = tools["saleswiki.approve_proposal"](pid, 7)
        self.assertEqual(noop["status"], "approved", "no-op echoes the current status")
        self.assertEqual(noop["reason"], "not in draft", "explicit machine-readable no-op marker")

    def test_revoke_envelope_signals_noop(self) -> None:
        svc, tools, pid = ToolHandlers._ttl_runtime()
        tools["saleswiki.approve_proposal"](pid)
        self.assertEqual(tools["saleswiki.revoke_proposal"](pid, "cleanup")["status"], "revoked")
        again = tools["saleswiki.revoke_proposal"](pid, "cleanup")
        self.assertEqual(again["reason"], "not an active grant")


@unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
class FastMcpWiring(unittest.TestCase):
    def test_server_builds_with_tools(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="mcp-"))
        vault = tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        svc = build_default_service(vault, tmp / "audit.jsonl", tmp / "proposals.jsonl", now=lambda: "t")
        actor = FixtureIdentityProvider("demo-ivan-ae", config.identity_config()).resolve()
        app = server.create_server(svc, actor)
        self.assertIsNotNone(app)

    def test_stdio_protocol_roundtrip(self) -> None:
        """Real protocol exercise: spawn the server over stdio and
        drive tools/list + tools/call, proving the dotted tool names actually work
        over MCP rather than only that create_server() returns non-None. Also pins
        the rendered text as content while the envelope semantics arrive as
        structuredContent (without duplicating the text)."""
        import asyncio
        import os

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        tmp = Path(tempfile.mkdtemp(prefix="mcp-proto-"))
        vault = tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        env = {k: os.environ[k] for k in ("PATH", "HOME", "SSL_CERT_FILE") if k in os.environ}
        env.update(
            SALESWIKI_DEMO_ACTOR="demo-broad-viewer",
            SALESWIKI_VAULT_ROOT=str(vault),
            SALESWIKI_RUNTIME_DIR=str(tmp / "runtime"),
            PYTHONPATH=str(ROOT),
        )
        params = StdioServerParameters(command=sys.executable, args=["-m", "saleswiki_mcp.server"], env=env)

        async def run():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    names = {t.name for t in listed.tools}
                    result = await session.call_tool("saleswiki.company_brief", {"company": "BluePeak Energy"})
                    text = "".join(getattr(c, "text", "") for c in result.content)
                    graph = await session.call_tool("saleswiki.entity_graph", {"entity": "BluePeak Energy"})
                    graph_text = "".join(getattr(c, "text", "") for c in graph.content)
                    return names, text, result.structuredContent, graph_text, graph.structuredContent

        names, text, structured, graph_text, graph_structured = asyncio.run(asyncio.wait_for(run(), timeout=30))
        self.assertIn("saleswiki.company_brief", names, "dotted tool name not exposed over the protocol")
        self.assertIn("BluePeak", text, "tools/call returned no usable content")
        self.assertIsInstance(structured, dict, "envelope semantics must ride structuredContent")
        self.assertIn("access", structured)
        self.assertNotIn("text", structured, "prose stays in content; structuredContent is semantics-only")
        self.assertIn("saleswiki.entity_graph", names)
        self.assertIn("BluePeak", graph_text)
        self.assertEqual(graph_structured["contract"], "saleswiki.graph-view")
        self.assertNotIn("text", graph_structured)


if __name__ == "__main__":
    unittest.main()
