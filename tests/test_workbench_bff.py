"""Security and protocol tests for the demo-only Workbench BFF."""

from __future__ import annotations

import asyncio
import http.client
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from integrations.workbench.server import DemoPersona, DemoSessionStore, McpGraphInvoker, WorkbenchApp, build_app_from_settings
from scripts import generate_demo_vault as gdv
from saleswiki_runtime.config import ConfigError, parse_runtime_settings


ROOT = Path(__file__).resolve().parents[1]


class FakeInvoker:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.failure = failure

    def invoke(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return {
            "contract": "saleswiki.graph-view",
            "version": 1,
            "access": "allowed",
            "root_id": "company_bluepeak",
            "summary": {
                "title": "BluePeak Energy", "conclusion": "Demo", "confidence": "high",
                "freshness": "current", "as_of": "2026-08-29", "next_action": "Review",
            },
            "nodes": [{
                "id": "company_bluepeak", "type": "company", "label": "BluePeak Energy",
                "subtitle": "", "detail": "", "metadata": {}, "evidence_ids": ["ev_1"],
            }],
            "edges": [],
            "evidence": [{
                "id": "ev_1", "title": "Company - BluePeak Energy", "status": "verified",
                "as_of": "2026-08-29", "summary": "Synthetic demo",
                "citation": {"boundary": "broad", "path": "demo/company.md"},
            }],
            "restricted": [],
            "missing": [],
        }

    def invoke_my_day(self) -> dict:
        self.calls.append({"tool": "my_day"})
        return {
            "title": "My Day", "access": "allowed", "conclusion": "Start with the hot lead.",
            "sections": [], "citations": [], "restricted": [], "confidence": "medium",
            "freshness": "fresh", "as_of": "2026-08-29", "next_action": "Open the account.",
            "missing": [], "redaction_notice": "", "text": "# My Day\n",
        }

    def invoke_import(self, *, target: str, summary: str) -> dict:
        self.calls.append({"tool": "import", "target": target, "summary": summary})
        return {"status": "draft", "proposal_id": "proposal-0042"}

    def invoke_review_queue(self) -> dict:
        self.calls.append({"tool": "review_queue"})
        return {"access": "allowed", "can_decide": True, "items": [{
            "proposal_id": "proposal-0042", "status": "draft", "type": "ingest_resource",
            "target": "company_bluepeak", "note": "company: BluePeak", "created": "2026-08-30T00:00:00Z",
        }]}

    def invoke_review_decision(self, *, proposal_id: str, action: str, reason: str) -> dict:
        self.calls.append({"tool": "review_decision", "proposal_id": proposal_id, "action": action, "reason": reason})
        return {"proposal_id": proposal_id, "status": "approved" if action == "approve" else "rejected"}

    def invoke_account_brief(self, *, entity: str) -> dict:
        self.calls.append({"tool": "account_brief", "entity": entity})
        return {"access": "allowed", "title": "Company Brief: BluePeak", "conclusion": "Review the next step.", "citations": [], "confidence": "medium"}

    def invoke_company_search(self, *, query: str) -> dict:
        self.calls.append({"tool": "company_search", "query": query})
        return {"status": "ok", "query": query, "items": [{"entity_id": "company_bluepeak", "label": "BluePeak Energy", "type": "company", "freshness": "fresh", "updated": "2026-08-29"}]}

    def invoke_dashboard(self) -> dict:
        self.calls.append({"tool": "dashboard"})
        return {"contract": "saleswiki.dashboard-view", "version": 1, "access": "allowed", "synthetic": True, "as_of": "2026-08-29", "history_status": "available", "risk": [], "coverage": [], "signals": [], "text": "Dashboard"}

    def invoke_guided_answer(self, *, intent: str, entity: str) -> dict:
        self.calls.append({"tool": "guided_answer", "intent": intent, "entity": entity})
        return {"intent": intent, "access": "allowed", "title": "Guided answer", "conclusion": "Use the permitted account context.", "citations": [], "confidence": "medium"}

    def invoke_update_proposal(self, *, target: str, note: str) -> dict:
        self.calls.append({"tool": "update", "target": target, "note": note})
        return {"proposal_id": "proposal-0043", "status": "draft"}


class RunningApp:
    def __init__(self, app: WorkbenchApp) -> None:
        from http.server import ThreadingHTTPServer

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.handler_class())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, *, method: str = "GET", headers: dict | None = None, body: bytes | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        body = response.read()
        result = response.status, dict(response.getheaders()), body
        conn.close()
        return result


class WorkbenchHttpTests(unittest.TestCase):
    def test_demo_persona_switch_uses_opaque_session_and_never_accepts_a_role(self) -> None:
        personas = {
            "demo-viewer": DemoPersona("demo-viewer", "Viewer", "employee-viewer", "company"),
            "demo-curator": DemoPersona("demo-curator", "Curator", "curator", "knowledge"),
        }
        observed: list[str] = []

        def invoker_for(actor_id: str):
            observed.append(actor_id)
            return FakeInvoker()

        app = WorkbenchApp(
            FakeInvoker(), invoker_factory=invoker_for,
            demo_sessions=DemoSessionStore("demo-viewer", personas),
            demo_personas=tuple(personas.values()), allow_fixture_persona_switching=True,
        )
        switch = json.dumps({"actor_id": "demo-curator"}).encode()
        malicious = json.dumps({"actor_id": "demo-curator", "role": "admin"}).encode()
        with RunningApp(app) as running:
            status, headers, body = running.request("/api/v1/session")
            cookie = headers["Set-Cookie"].split(";", 1)[0]
            switched, _, switched_body = running.request(
                "/api/v1/demo-persona", method="POST",
                headers={"Cookie": cookie, "Content-Type": "application/json", "Content-Length": str(len(switch))}, body=switch,
            )
            forbidden, _, _ = running.request(
                "/api/v1/demo-persona", method="POST",
                headers={"Cookie": cookie, "Content-Type": "application/json", "Content-Length": str(len(malicious))}, body=malicious,
            )
            graph, _, _ = running.request("/api/v1/entity-graph?entity=BluePeak", headers={"Cookie": cookie})
        self.assertEqual((status, switched, forbidden, graph), (200, 200, 400, 200))
        self.assertEqual(json.loads(body)["person"]["role"], "employee-viewer")
        self.assertFalse(json.loads(body)["can_review"])
        self.assertEqual(json.loads(switched_body)["person"], personas["demo-curator"].public())
        self.assertTrue(json.loads(switched_body)["can_review"])
        self.assertEqual(observed, ["demo-curator"])

    def test_account_brief_and_update_keep_identity_server_owned(self) -> None:
        fake = FakeInvoker()
        update = json.dumps({"target": "company_bluepeak", "note": "Confirm the next meeting."}).encode()
        with RunningApp(WorkbenchApp(fake)) as running:
            brief_status, brief_headers, brief_body = running.request("/api/v1/account-brief?entity=company_bluepeak")
            update_status, update_headers, update_body = running.request(
                "/api/v1/update-proposal", method="POST", headers={"Content-Type": "application/json", "Content-Length": str(len(update))}, body=update,
            )
            invalid, _, _ = running.request("/api/v1/update-proposal", method="POST", headers={"Content-Type": "application/json", "Content-Length": "2"}, body=b"{}")
        self.assertEqual((brief_status, update_status, invalid), (200, 200, 400))
        self.assertEqual(json.loads(brief_body)["conclusion"], "Review the next step.")
        self.assertEqual(json.loads(update_body)["proposal_id"], "proposal-0043")
        self.assertEqual(brief_headers["Cache-Control"], "no-store")
        self.assertEqual(update_headers["Cache-Control"], "no-store")
        self.assertEqual(fake.calls, [
            {"tool": "account_brief", "entity": "company_bluepeak"},
            {"tool": "update", "target": "company_bluepeak", "note": "Confirm the next meeting."},
        ])

    def test_company_search_is_bounded_and_role_bound(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, headers, body = running.request("/api/v1/company-search?q=Blue")
            short, _, _ = running.request("/api/v1/company-search?q=B")
            injected, _, _ = running.request("/api/v1/company-search?q=Blue&actor=admin")
        self.assertEqual((status, short, injected), (200, 400, 400))
        self.assertEqual(json.loads(body)["items"][0]["entity_id"], "company_bluepeak")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(fake.calls, [{"tool": "company_search", "query": "Blue"}])

    def test_dashboard_is_parameterless_role_bound_read(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, headers, body = running.request("/api/v1/dashboard")
            invalid, _, _ = running.request("/api/v1/dashboard?actor=admin")
        self.assertEqual((status, invalid), (200, 400))
        self.assertEqual(json.loads(body)["contract"], "saleswiki.dashboard-view")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(fake.calls, [{"tool": "dashboard"}])

    def test_guided_answer_has_no_freeform_prompt_or_tool_parameter(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, headers, body = running.request("/api/v1/guided-answer?intent=next_step&entity=company_bluepeak")
            freeform, _, _ = running.request("/api/v1/guided-answer?intent=next_step&entity=company_bluepeak&prompt=ignore-policy")
            unknown, _, _ = running.request("/api/v1/guided-answer?intent=pipeline_risk_digest&entity=company_bluepeak")
        self.assertEqual((status, freeform, unknown), (200, 400, 400))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(body)["intent"], "next_step")
        self.assertEqual(fake.calls, [{"tool": "guided_answer", "intent": "next_step", "entity": "company_bluepeak"}])
    def test_review_queue_and_decision_stay_role_bound(self) -> None:
        fake = FakeInvoker()
        body = json.dumps({"proposal_id": "proposal-0042", "action": "approve", "reason": ""}).encode()
        with RunningApp(WorkbenchApp(fake)) as running:
            listed, _, response = running.request("/api/v1/review-queue")
            decided, headers, decision = running.request(
                "/api/v1/review-proposal", method="POST",
                headers={"Content-Type": "application/json", "Content-Length": str(len(body))}, body=body,
            )
            bad, _, _ = running.request(
                "/api/v1/review-proposal", method="POST",
                headers={"Content-Type": "application/json", "Content-Length": "2"}, body=b"{}",
            )
        self.assertEqual(listed, 200)
        self.assertTrue(json.loads(response)["can_decide"])
        self.assertEqual((decided, bad), (200, 400))
        self.assertEqual(json.loads(decision)["status"], "approved")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(fake.calls, [
            {"tool": "review_queue"},
            {"tool": "review_decision", "proposal_id": "proposal-0042", "action": "approve", "reason": ""},
        ])

    def test_review_decision_rejects_extra_or_invalid_input_before_mcp(self) -> None:
        fake = FakeInvoker()
        invalid_action = json.dumps({"proposal_id": "proposal-0042", "action": "archive", "reason": ""}).encode()
        extra = json.dumps({"proposal_id": "proposal-0042", "action": "approve", "reason": "", "actor": "admin"}).encode()
        with RunningApp(WorkbenchApp(fake)) as running:
            first, _, _ = running.request("/api/v1/review-proposal", method="POST", headers={"Content-Type": "application/json", "Content-Length": str(len(invalid_action))}, body=invalid_action)
            second, _, _ = running.request("/api/v1/review-proposal", method="POST", headers={"Content-Type": "application/json", "Content-Length": str(len(extra))}, body=extra)
        self.assertEqual((first, second), (400, 400))
        self.assertEqual(fake.calls, [])

    def test_import_accepts_only_a_small_review_summary(self) -> None:
        fake = FakeInvoker()
        body = json.dumps({"target": "company_bluepeak", "summary": "company: BluePeak Energy"}).encode()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, headers, response = running.request(
                "/api/v1/import-proposal", method="POST",
                headers={"Content-Type": "application/json", "Content-Length": str(len(body))}, body=body,
            )
            invalid, _, _ = running.request("/api/v1/import-proposal", method="POST", headers={"Content-Length": "0"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(response)["proposal_id"], "proposal-0042")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(invalid, 400)
        self.assertEqual(fake.calls, [{"tool": "import", "target": "company_bluepeak", "summary": "company: BluePeak Energy"}])

    def test_my_day_has_a_parameterless_role_bound_endpoint(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, _, body = running.request("/api/v1/my-day")
            invalid, _, _ = running.request("/api/v1/my-day?actor=admin")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["title"], "My Day")
        self.assertEqual(invalid, 400)
        self.assertEqual(fake.calls, [{"tool": "my_day"}])
    def test_graph_endpoint_forwards_only_allowlisted_graph_inputs(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, headers, body = running.request(
                "/api/v1/entity-graph?entity=BluePeak%20Energy&include=deal,call"
            )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["contract"], "saleswiki.graph-view")
        self.assertEqual(
            fake.calls,
            [{"entity": "BluePeak Energy", "entity_type": "company", "depth": 1,
              "include": ["deal", "call"]}],
        )
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_browser_cannot_supply_actor_or_role(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, _, body = running.request(
                "/api/v1/entity-graph?entity=BluePeak&actor=admin"
            )
            role_status, _, _ = running.request(
                "/api/v1/entity-graph?entity=BluePeak&role=admin"
            )
        self.assertEqual((status, role_status), (400, 400))
        self.assertEqual(json.loads(body)["error"], "invalid_query")
        self.assertEqual(fake.calls, [])

    def test_invalid_and_oversized_entities_are_rejected_before_mcp(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            missing, _, _ = running.request("/api/v1/entity-graph")
            oversized, _, _ = running.request(
                "/api/v1/entity-graph?entity=" + ("x" * 201)
            )
            duplicate, _, _ = running.request(
                "/api/v1/entity-graph?entity=one&entity=two"
            )
        self.assertEqual((missing, oversized, duplicate), (400, 400, 400))
        self.assertEqual(fake.calls, [])

    def test_backend_error_is_generic_and_does_not_echo_secret_or_input(self) -> None:
        fake = FakeInvoker(failure=RuntimeError("TOKEN=super-secret for BluePeak"))
        with RunningApp(WorkbenchApp(fake)) as running:
            status, _, body = running.request(
                "/api/v1/entity-graph?entity=BluePeak"
            )
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body)["error"], "graph_backend_unavailable")
        self.assertNotIn(b"secret", body)
        self.assertNotIn(b"BluePeak", body)

    def test_health_is_minimal_and_does_not_call_mcp(self) -> None:
        fake = FakeInvoker()
        with RunningApp(WorkbenchApp(fake)) as running:
            status, headers, body = running.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(fake.calls, [])

    def test_non_read_methods_return_safe_json(self) -> None:
        with RunningApp(WorkbenchApp(FakeInvoker())) as running:
            status, headers, body = running.request(
                "/api/v1/entity-graph?entity=BluePeak", method="POST"
            )
        self.assertEqual(status, 405)
        self.assertEqual(json.loads(body)["error"], "method_not_allowed")
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_same_origin_default_and_explicit_cors_allowlist(self) -> None:
        with RunningApp(WorkbenchApp(FakeInvoker())) as running:
            host = f"127.0.0.1:{running.server.server_port}"
            same, _, _ = running.request(
                "/api/v1/entity-graph?entity=BluePeak",
                headers={"Origin": f"http://{host}", "Host": host},
            )
            cross, _, _ = running.request(
                "/api/v1/entity-graph?entity=BluePeak",
                headers={"Origin": "https://evil.invalid"},
            )
        self.assertEqual(same, 200)
        self.assertEqual(cross, 403)

        origin = "http://127.0.0.1:4173"
        with RunningApp(WorkbenchApp(FakeInvoker(), allowed_origins=(origin,))) as running:
            status, headers, _ = running.request(
                "/api/v1/entity-graph?entity=BluePeak", headers={"Origin": origin}
            )
            options, option_headers, _ = running.request(
                "/api/v1/entity-graph", method="OPTIONS", headers={"Origin": origin}
            )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], origin)
        self.assertEqual(options, 204)
        self.assertEqual(option_headers["Access-Control-Allow-Methods"], "GET, OPTIONS")

    def test_malformed_and_oversized_graphs_are_rejected(self) -> None:
        malformed = FakeInvoker()
        malformed.invoke = lambda **_kwargs: {"contract": "wrong"}
        oversized = FakeInvoker()
        oversized.invoke = lambda **_kwargs: {
            "contract": "saleswiki.graph-view", "version": 1, "access": "allowed",
            "root_id": "root", "summary": {}, "nodes": [{}] * 41, "edges": [],
            "evidence": [], "restricted": [], "missing": [],
        }
        for invoker in (malformed, oversized):
            with RunningApp(WorkbenchApp(invoker)) as running:
                status, _, body = running.request("/api/v1/entity-graph?entity=BluePeak")
            self.assertEqual(status, 502)
            self.assertEqual(json.loads(body)["error"], "graph_backend_invalid")

    def test_unserializable_graph_is_rejected_without_connection_failure(self) -> None:
        invoker = FakeInvoker()
        invoker.invoke = lambda **_kwargs: {
            "contract": "saleswiki.graph-view", "version": 1, "access": "allowed",
            "root_id": "root", "summary": {}, "nodes": [{"bad": object()}],
            "edges": [], "evidence": [], "restricted": [], "missing": [],
        }
        with RunningApp(WorkbenchApp(invoker)) as running:
            status, _, body = running.request("/api/v1/entity-graph?entity=BluePeak")
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body)["error"], "graph_backend_invalid")

    def test_access_state_invariants_are_rejected(self) -> None:
        allowed_empty = FakeInvoker()
        allowed_empty.invoke = lambda **_kwargs: {
            "contract": "saleswiki.graph-view", "version": 1, "access": "allowed",
            "root_id": None, "summary": {}, "nodes": [], "edges": [], "evidence": [],
            "restricted": [], "missing": [],
        }
        blocked_with_records = FakeInvoker()
        blocked_graph = FakeInvoker().invoke()
        blocked_graph.update(access="blocked", root_id=None)
        blocked_with_records.invoke = lambda **_kwargs: blocked_graph
        for invoker in (allowed_empty, blocked_with_records):
            with RunningApp(WorkbenchApp(invoker)) as running:
                status, _, body = running.request("/api/v1/entity-graph?entity=BluePeak")
            self.assertEqual(status, 502)
            self.assertEqual(json.loads(body)["error"], "graph_backend_invalid")

    def test_concurrency_is_bounded(self) -> None:
        fake = FakeInvoker()
        app = WorkbenchApp(fake, request_slots=threading.BoundedSemaphore(1))
        self.assertTrue(app.request_slots.acquire(blocking=False))
        with RunningApp(app) as running:
            status, _, body = running.request("/api/v1/entity-graph?entity=BluePeak")
        app.request_slots.release()
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"], "graph_backend_busy")


class WorkbenchStartupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="workbench-bff-"))

    def settings(
        self, vault: Path, *, enabled: bool = True, host: str = "127.0.0.1",
        origins: tuple[str, ...] = (), profile: str = "demo"
    ):
        origin_text = ", ".join(json.dumps(value) for value in origins)
        path = self.tmp / f"runtime-{len(list(self.tmp.glob('runtime-*.toml')))}.toml"
        path.write_text(
            f'''version = 1
profile = "{profile}"
[vault]
root = {json.dumps(str(vault))}
runtime = {json.dumps(str(self.tmp / "runtime"))}
[workbench]
enabled = {str(enabled).lower()}
host = {json.dumps(host)}
port = 8787
identity_provider = "fixture"
mcp_transport = "stdio"
allowed_origins = [{origin_text}]
''', encoding="utf-8"
        )
        return parse_runtime_settings(path)

    def test_actor_is_resolved_only_from_server_environment(self) -> None:
        vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        app = build_app_from_settings(self.settings(vault), {
            "SALESWIKI_DEMO_ACTOR": "demo-broad-viewer",
        })
        self.assertEqual(app.invoker.actor_id, "demo-broad-viewer")

    def test_non_demo_vault_fails_closed(self) -> None:
        vault = self.tmp / "production"
        vault.mkdir()
        (vault / "Company.md").write_text(
            "---\ndataset: production\n---\n# Company\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(RuntimeError, "refusing to serve"):
            build_app_from_settings(self.settings(vault), {
                "SALESWIKI_DEMO_ACTOR": "demo-broad-viewer",
            })

    def test_generic_production_override_cannot_broaden_demo_only_bff(self) -> None:
        vault = self.tmp / "production-override"
        vault.mkdir()
        (vault / "Company.md").write_text(
            "---\ndataset: production\n---\n# Company\n", encoding="utf-8"
        )
        with mock.patch.dict(os.environ, {"SALESWIKI_ALLOW_PROD_VAULT": "1"}):
            with self.assertRaisesRegex(ConfigError, "demo/synthetic"):
                build_app_from_settings(
                    self.settings(vault), {"SALESWIKI_DEMO_ACTOR": "demo-broad-viewer"}
                )

    def test_unknown_fixture_actor_fails_at_startup(self) -> None:
        vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        with self.assertRaises(KeyError):
            build_app_from_settings(self.settings(vault), {
                "SALESWIKI_DEMO_ACTOR": "not-a-real-actor",
            })

    def test_disabled_and_non_loopback_profiles_fail_closed(self) -> None:
        vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        actor = {"SALESWIKI_DEMO_ACTOR": "demo-broad-viewer"}
        with self.assertRaisesRegex(ConfigError, "disabled"):
            build_app_from_settings(self.settings(vault, enabled=False), actor)
        with self.assertRaisesRegex(ConfigError, "non-loopback"):
            build_app_from_settings(self.settings(vault, host="0.0.0.0"), actor)

    def test_origins_are_exact_and_reject_credentials_paths_and_newlines(self) -> None:
        vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(vault)
        actor = {"SALESWIKI_DEMO_ACTOR": "demo-broad-viewer"}
        for origin in (
            "https://user@example.com", "https://example.com/path",
            "https://example.com?x=1", "https://example.com/#x", "javascript:alert(1)",
            "https://example.com\nX-Evil: yes",
            "https://example.com:not-a-port",
        ):
            with self.subTest(origin=origin), self.assertRaises(ConfigError):
                build_app_from_settings(self.settings(vault, origins=(origin,)), actor)


class McpTimeoutTests(unittest.TestCase):
    def test_timeout_is_hard_bounded(self) -> None:
        invoker = McpGraphInvoker("demo", Path("."), Path("."), timeout_seconds=0.01)

        async def slow(**_kwargs):
            await asyncio.sleep(1)
            return {}

        object.__setattr__(invoker, "_invoke_async", slow)
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            invoker.invoke(entity="x", entity_type="company", depth=1, include=None)
        self.assertLess(time.monotonic() - started, 0.5)


@unittest.skipUnless(importlib.util.find_spec("mcp"), "official MCP SDK not installed")
class WorkbenchRealMcpRoundTrip(unittest.TestCase):
    def test_real_stdio_graph_round_trip(self) -> None:
        vault = Path(tempfile.mkdtemp(prefix="workbench-mcp-")) / "permissioned"
        gdv.generate_permissioned_demo(vault)
        settings = WorkbenchStartupTests()
        settings.tmp = vault.parent
        app = build_app_from_settings(settings.settings(vault), {
            "SALESWIKI_DEMO_ACTOR": "demo-broad-viewer",
        })
        graph = app.invoker.invoke(
            entity="BluePeak Energy", entity_type="company", depth=1, include=None
        )
        self.assertEqual(graph["contract"], "saleswiki.graph-view")
        self.assertIn(graph["access"], {"allowed", "sanitized"})


if __name__ == "__main__":
    unittest.main()
