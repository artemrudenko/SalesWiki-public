"""Small, demo-only HTTP bridge from the Workbench UI to MCP stdio.

The browser never chooses an actor or role.  One fixture actor is resolved from
the BFF process environment and is forwarded to the child MCP process.  The
demo-vault guard runs before the HTTP server starts.
"""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import os
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Mapping, Protocol
from urllib.parse import parse_qs, urlsplit

from saleswiki_mcp import config, vault_guard
from saleswiki_mcp.graph import (
    MAX_EDGES,
    MAX_EVIDENCE,
    MAX_NODES,
    SUPPORTED_INCLUDE,
    GraphProjectionError,
    GraphProjector,
)
from saleswiki_mcp.identity import FixtureIdentityProvider
from saleswiki_runtime.config import ConfigError, RuntimeSettings, load_runtime_settings
from .sessions import DemoPersona, DemoSessionStore, SESSION_COOKIE, SESSION_TTL_SECONDS


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VAULT = ROOT / "demo" / "permissioned"
DEFAULT_RUNTIME = ROOT / ".runtime" / "workbench"
MAX_ENTITY_LENGTH = 200
MAX_SEARCH_QUERY_LENGTH = 120
MAX_INCLUDE_ITEMS = 12
MCP_TIMEOUT_SECONDS = 15.0
MAX_CONCURRENT_REQUESTS = 4
MAX_RESPONSE_BYTES = 1_000_000
MAX_IMPORT_BODY_BYTES = 1_024
MAX_IMPORT_TARGET_LENGTH = 200
MAX_IMPORT_SUMMARY_LENGTH = 480
MAX_REVIEW_BODY_BYTES = 768
MAX_PROPOSAL_ID_LENGTH = 40
MAX_REJECTION_REASON_LENGTH = 240
MAX_UPDATE_BODY_BYTES = 768
MAX_UPDATE_NOTE_LENGTH = 480
MAX_SESSION_ACTOR_LENGTH = 80
ALLOWED_QUERY = frozenset({"entity", "entity_type", "depth", "include"})
ALLOWED_SEARCH_QUERY = frozenset({"q"})
ALLOWED_GUIDED_QUERY = frozenset({"intent", "entity"})
GUIDED_INTENTS = frozenset({"account_brief", "what_changed", "next_step", "deal_risk", "call_prep"})
REVIEWER_ROLES = frozenset({"curator", "hos", "revops", "admin"})


class GraphInvoker(Protocol):
    def invoke(self, *, entity: str, entity_type: str, depth: int, include: list[str] | None) -> dict: ...

    def invoke_my_day(self) -> dict: ...

    def invoke_import(self, *, target: str, summary: str) -> dict: ...

    def invoke_review_queue(self) -> dict: ...

    def invoke_review_decision(self, *, proposal_id: str, action: str, reason: str) -> dict: ...

    def invoke_account_brief(self, *, entity: str) -> dict: ...

    def invoke_update_proposal(self, *, target: str, note: str) -> dict: ...

    def invoke_company_search(self, *, query: str) -> dict: ...

    def invoke_dashboard(self) -> dict: ...

    def invoke_guided_answer(self, *, intent: str, entity: str) -> dict: ...


def _child_env(**values: str) -> dict[str, str]:
    """Build an intentionally small child environment; do not forward secrets."""
    env = {key: os.environ[key] for key in ("PATH", "HOME", "SSL_CERT_FILE") if key in os.environ}
    env.update(values)
    return env


@dataclass(frozen=True)
class McpGraphInvoker:
    actor_id: str
    vault_root: Path
    runtime_dir: Path
    timeout_seconds: float = MCP_TIMEOUT_SECONDS

    def invoke(self, *, entity: str, entity_type: str, depth: int, include: list[str] | None) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(
                self._invoke_async(entity=entity, entity_type=entity_type, depth=depth, include=include),
                timeout=self.timeout_seconds,
            )

        return asyncio.run(bounded())

    def invoke_my_day(self) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(self._invoke_my_day_async(), timeout=self.timeout_seconds)
        return asyncio.run(bounded())

    def invoke_import(self, *, target: str, summary: str) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(self._invoke_import_async(target, summary), timeout=self.timeout_seconds)
        return asyncio.run(bounded())

    def invoke_review_queue(self) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(self._invoke_review_queue_async(), timeout=self.timeout_seconds)
        return asyncio.run(bounded())

    def invoke_review_decision(self, *, proposal_id: str, action: str, reason: str) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(
                self._invoke_review_decision_async(proposal_id, action, reason), timeout=self.timeout_seconds
            )
        return asyncio.run(bounded())

    def invoke_account_brief(self, *, entity: str) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(self._invoke_governance_tool("saleswiki.company_brief", {"company": entity}), timeout=self.timeout_seconds)
        return asyncio.run(bounded())

    def invoke_company_search(self, *, query: str) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(
                self._invoke_governance_tool("saleswiki.company_search", {"query": query}),
                timeout=self.timeout_seconds,
            )
        return asyncio.run(bounded())

    def invoke_dashboard(self) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(
                self._invoke_governance_tool("saleswiki.dashboard", {"scope": ""}),
                timeout=self.timeout_seconds,
            )
        return asyncio.run(bounded())

    def invoke_guided_answer(self, *, intent: str, entity: str) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(
                self._invoke_governance_tool("saleswiki.guided_answer", {"intent": intent, "company": entity}),
                timeout=self.timeout_seconds,
            )
        return asyncio.run(bounded())

    def invoke_update_proposal(self, *, target: str, note: str) -> dict:
        async def bounded() -> dict:
            return await asyncio.wait_for(self._invoke_governance_tool("saleswiki.flag_stale_or_wrong", {"target": target, "note": note}), timeout=self.timeout_seconds)
        return asyncio.run(bounded())

    async def _invoke_my_day_async(self) -> dict:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        env = _child_env(
            SALESWIKI_DEMO_ACTOR=self.actor_id, SALESWIKI_VAULT_ROOT=str(self.vault_root),
            SALESWIKI_RUNTIME_DIR=str(self.runtime_dir), PYTHONPATH=str(ROOT),
        )
        params = StdioServerParameters(command=sys.executable, args=["-m", "saleswiki_mcp.server"], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("saleswiki.my_day", {"scope": ""})
        if getattr(result, "isError", False) or not isinstance(result.structuredContent, dict):
            raise RuntimeError("MCP tool returned an error")
        return result.structuredContent

    async def _invoke_import_async(self, target: str, summary: str) -> dict:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        env = _child_env(
            SALESWIKI_DEMO_ACTOR=self.actor_id, SALESWIKI_VAULT_ROOT=str(self.vault_root),
            SALESWIKI_RUNTIME_DIR=str(self.runtime_dir), PYTHONPATH=str(ROOT),
        )
        params = StdioServerParameters(command=sys.executable, args=["-m", "saleswiki_mcp.server"], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("saleswiki.ingest_resource", {"target": target, "note": summary})
        if getattr(result, "isError", False) or not isinstance(result.structuredContent, dict):
            raise RuntimeError("MCP tool returned an error")
        return result.structuredContent

    async def _invoke_review_queue_async(self) -> dict:
        return await self._invoke_governance_tool("saleswiki.review_queue", {"scope": ""})

    async def _invoke_review_decision_async(self, proposal_id: str, action: str, reason: str) -> dict:
        if action == "approve":
            return await self._invoke_governance_tool("saleswiki.approve_proposal", {"proposal_id": proposal_id})
        return await self._invoke_governance_tool(
            "saleswiki.reject_proposal", {"proposal_id": proposal_id, "reason": reason}
        )

    async def _invoke_governance_tool(self, tool: str, arguments: dict) -> dict:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        env = _child_env(
            SALESWIKI_DEMO_ACTOR=self.actor_id, SALESWIKI_VAULT_ROOT=str(self.vault_root),
            SALESWIKI_RUNTIME_DIR=str(self.runtime_dir), PYTHONPATH=str(ROOT),
        )
        params = StdioServerParameters(command=sys.executable, args=["-m", "saleswiki_mcp.server"], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
        if getattr(result, "isError", False) or not isinstance(result.structuredContent, dict):
            raise RuntimeError("MCP tool returned an error")
        return result.structuredContent

    async def _invoke_async(
        self, *, entity: str, entity_type: str, depth: int, include: list[str] | None
    ) -> dict:
        # Official SDK imports stay here so tests with a fake invoker do not need
        # the optional MCP dependency installed.
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = _child_env(
            SALESWIKI_DEMO_ACTOR=self.actor_id,
            SALESWIKI_VAULT_ROOT=str(self.vault_root),
            SALESWIKI_RUNTIME_DIR=str(self.runtime_dir),
            PYTHONPATH=str(ROOT),
        )
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "saleswiki_mcp.server"],
            env=env,
        )
        arguments: dict[str, object] = {
            "entity": entity,
            "entity_type": entity_type,
            "depth": depth,
        }
        if include:
            arguments["include"] = include
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("saleswiki.entity_graph", arguments)
        if getattr(result, "isError", False):
            raise RuntimeError("MCP tool returned an error")
        graph = result.structuredContent
        _validate_graph_view(graph)
        return graph


@dataclass(frozen=True)
class WorkbenchApp:
    invoker: GraphInvoker
    allowed_origins: tuple[str, ...] = ()
    # `invoker` keeps the simple unit-test shape.  The real demo supplies the
    # factory so each opaque server session can resolve its fixture persona.
    invoker_factory: Callable[[str], GraphInvoker] | None = None
    demo_sessions: DemoSessionStore | None = None
    demo_personas: tuple[DemoPersona, ...] = ()
    allow_fixture_persona_switching: bool = False
    request_slots: threading.BoundedSemaphore = field(
        default_factory=lambda: threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS),
        compare=False,
    )

    def handler_class(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "SalesWikiWorkbench/1"
            sys_version = ""

            def log_message(self, _format: str, *_args) -> None:
                # Avoid logging user-controlled query strings through BaseHTTPRequestHandler.
                return

            def _headers(self, status: int, *, length: int, request_id: str, session_id: str | None = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(length))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Request-ID", request_id)
                if session_id:
                    # HttpOnly means JavaScript cannot steal or alter the
                    # opaque id; SameSite protects the loopback demo from
                    # cross-site form posts.  This is not a substitute for
                    # authenticated OIDC in a shared deployment.
                    self.send_header("Set-Cookie", f"{SESSION_COOKIE}={session_id}; Path=/api/v1; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL_SECONDS}")
                origin = self.headers.get("Origin", "")
                if origin and origin in app.allowed_origins:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                self.end_headers()

            def _json(self, status: int, payload: dict, *, route: str = "unknown", session_id: str | None = None) -> None:
                request_id = uuid.uuid4().hex
                if status >= 400:
                    payload = {**payload, "request_id": request_id}
                body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self._headers(status, length=len(body), request_id=request_id, session_id=session_id)
                self.wfile.write(body)
                print(
                    f"workbench request_id={request_id} method={self.command} route={route} status={status}",
                    file=sys.stderr,
                )

            def _origin_allowed(self) -> bool:
                origin = self.headers.get("Origin", "")
                if not origin:
                    return True
                if app.allowed_origins:
                    return origin in app.allowed_origins
                # No CORS configuration means same-origin only.  A browser may
                # still attach Origin to a same-origin request, so compare it to
                # the request authority instead of rejecting it blindly.
                host = self.headers.get("Host", "")
                return origin in {f"http://{host}", f"https://{host}"}

            def do_OPTIONS(self) -> None:
                if not self._origin_allowed() or not app.allowed_origins:
                    self._json(403, {"error": "origin_not_allowed"}, route="preflight")
                    return
                parsed = urlsplit(self.path)
                if parsed.path not in {"/api/v1/session", "/api/v1/entity-graph", "/api/v1/dashboard", "/api/v1/guided-answer", "/api/v1/account-brief", "/api/v1/review-queue", "/api/v1/import-proposal", "/api/v1/review-proposal", "/api/v1/update-proposal", "/api/v1/demo-persona"}:
                    self._json(404, {"error": "not_found"}, route="preflight")
                    return
                request_id = uuid.uuid4().hex
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Request-ID", request_id)
                self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
                methods = "GET, OPTIONS" if parsed.path in {"/api/v1/session", "/api/v1/entity-graph", "/api/v1/dashboard", "/api/v1/guided-answer", "/api/v1/account-brief", "/api/v1/review-queue"} else "POST, OPTIONS"
                self.send_header("Access-Control-Allow-Methods", methods)
                self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type")
                self.send_header("Vary", "Origin")
                self.end_headers()
                print(
                    f"workbench request_id={request_id} method=OPTIONS route=preflight status=204",
                    file=sys.stderr,
                )

            def _method_not_allowed(self) -> None:
                self._json(405, {"error": "method_not_allowed"}, route="method")

            def _actor_and_invoker(self) -> tuple[str, GraphInvoker]:
                actor_id = app.demo_sessions.resolve(self.headers.get("Cookie", ""))[0] if app.demo_sessions else ""
                return actor_id, app.invoker_factory(actor_id) if app.invoker_factory else app.invoker

            def _session_payload(self, actor_id: str) -> dict:
                persona = next((item for item in app.demo_personas if item.id == actor_id), None)
                if persona is None:
                    raise ValueError("unknown demo persona")
                return {
                    "mode": "demo-fixture",
                    "person": persona.public(),
                    "can_review": persona.role in REVIEWER_ROLES,
                    "can_switch_persona": app.allow_fixture_persona_switching,
                    "personas": [item.public() for item in app.demo_personas] if app.allow_fixture_persona_switching else [],
                }

            def do_POST(self) -> None:
                if not self._origin_allowed():
                    self._json(403, {"error": "origin_not_allowed"}, route="origin")
                    return
                parsed = urlsplit(self.path)
                if parsed.path not in {"/api/v1/import-proposal", "/api/v1/review-proposal", "/api/v1/update-proposal", "/api/v1/demo-persona"}:
                    self._method_not_allowed()
                    return
                if parsed.query:
                    self._json(400, {"error": "invalid_request"}, route="write")
                    return
                if parsed.path == "/api/v1/demo-persona":
                    if not app.demo_sessions or not app.allow_fixture_persona_switching:
                        self._json(404, {"error": "not_found"}, route="persona")
                        return
                    try:
                        actor_id = _parse_demo_persona(self.headers, self.rfile)
                    except ValueError as exc:
                        self._json(400, {"error": str(exc)}, route="persona")
                        return
                    _current, session_id = app.demo_sessions.resolve(self.headers.get("Cookie", ""))
                    if not session_id:
                        self._json(401, {"error": "demo_session_required"}, route="persona")
                        return
                    switched = app.demo_sessions.switch(session_id, actor_id)
                    if not switched:
                        self._json(400, {"error": "invalid_demo_persona"}, route="persona")
                        return
                    self._json(200, self._session_payload(switched), route="persona", session_id=session_id)
                    return
                if parsed.path == "/api/v1/review-proposal":
                    try:
                        request = _parse_review_decision(self.headers, self.rfile)
                    except ValueError as exc:
                        self._json(400, {"error": str(exc)}, route="review")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "review_backend_busy"}, route="review")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        result = invoker.invoke_review_decision(**request)
                        _validate_review_decision(result)
                    except Exception:
                        self._json(502, {"error": "review_backend_unavailable"}, route="review")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, result, route="review")
                    return
                if parsed.path == "/api/v1/update-proposal":
                    try:
                        request = _parse_update_proposal(self.headers, self.rfile)
                    except ValueError as exc:
                        self._json(400, {"error": str(exc)}, route="update")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "update_backend_busy"}, route="update")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        proposal = invoker.invoke_update_proposal(**request)
                        _validate_import_proposal(proposal)
                    except Exception:
                        self._json(502, {"error": "update_backend_unavailable"}, route="update")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, proposal, route="update")
                    return
                try:
                    request = _parse_import_request(self.headers, self.rfile)
                except ValueError as exc:
                    self._json(400, {"error": str(exc)}, route="import")
                    return
                if not app.request_slots.acquire(blocking=False):
                    self._json(503, {"error": "import_backend_busy"}, route="import")
                    return
                try:
                    _actor, invoker = self._actor_and_invoker()
                    proposal = invoker.invoke_import(**request)
                    _validate_import_proposal(proposal)
                except Exception:
                    self._json(502, {"error": "import_backend_unavailable"}, route="import")
                    return
                finally:
                    app.request_slots.release()
                self._json(200, proposal, route="import")

            do_PUT = _method_not_allowed
            do_PATCH = _method_not_allowed
            do_DELETE = _method_not_allowed

            def do_GET(self) -> None:
                if not self._origin_allowed():
                    self._json(403, {"error": "origin_not_allowed"}, route="origin")
                    return
                parsed = urlsplit(self.path)
                if parsed.path == "/health":
                    self._json(200, {"status": "ok"}, route="health")
                    return
                if parsed.path == "/api/v1/session":
                    if not app.demo_sessions:
                        self._json(404, {"error": "not_found"}, route="session")
                        return
                    actor_id, session_id = app.demo_sessions.resolve(self.headers.get("Cookie", ""))
                    if not session_id:
                        actor_id, session_id = app.demo_sessions.create()
                    self._json(200, self._session_payload(actor_id), route="session", session_id=session_id)
                    return
                if parsed.path == "/api/v1/my-day":
                    if parsed.query:
                        self._json(400, {"error": "invalid_query"}, route="my_day")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "daily_backend_busy"}, route="my_day")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        daily = invoker.invoke_my_day()
                        _validate_answer(daily)
                    except Exception:
                        self._json(502, {"error": "daily_backend_unavailable"}, route="my_day")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, daily, route="my_day")
                    return
                if parsed.path == "/api/v1/dashboard":
                    if parsed.query:
                        self._json(400, {"error": "invalid_query"}, route="dashboard")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "dashboard_backend_busy"}, route="dashboard")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        dashboard = invoker.invoke_dashboard()
                        _validate_dashboard(dashboard)
                    except Exception:
                        self._json(502, {"error": "dashboard_backend_unavailable"}, route="dashboard")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, dashboard, route="dashboard")
                    return
                if parsed.path == "/api/v1/guided-answer":
                    try:
                        request = _parse_guided_query(parsed.query)
                    except ValueError as exc:
                        self._json(400, {"error": str(exc)}, route="guided_answer")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "guided_backend_busy"}, route="guided_answer")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        answer = invoker.invoke_guided_answer(**request)
                        _validate_guided_answer(answer, request["intent"])
                    except Exception:
                        self._json(502, {"error": "guided_backend_unavailable"}, route="guided_answer")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, answer, route="guided_answer")
                    return
                if parsed.path == "/api/v1/review-queue":
                    if parsed.query:
                        self._json(400, {"error": "invalid_query"}, route="review_queue")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "review_backend_busy"}, route="review_queue")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        queue = invoker.invoke_review_queue()
                        _validate_review_queue(queue)
                    except Exception:
                        self._json(502, {"error": "review_backend_unavailable"}, route="review_queue")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, queue, route="review_queue")
                    return
                if parsed.path == "/api/v1/account-brief":
                    query = _parse_graph_query(parsed.query)
                    if query.get("entity_type") != "company" or query.get("depth") != 1 or query.get("include"):
                        self._json(400, {"error": "invalid_query"}, route="account_brief")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "brief_backend_busy"}, route="account_brief")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        brief = invoker.invoke_account_brief(entity=query["entity"])
                        _validate_account_brief(brief)
                    except Exception:
                        self._json(502, {"error": "brief_backend_unavailable"}, route="account_brief")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, brief, route="account_brief")
                    return
                if parsed.path == "/api/v1/company-search":
                    try:
                        query = _parse_search_query(parsed.query)
                    except ValueError as exc:
                        self._json(400, {"error": str(exc)}, route="company_search")
                        return
                    if not app.request_slots.acquire(blocking=False):
                        self._json(503, {"error": "search_backend_busy"}, route="company_search")
                        return
                    try:
                        _actor, invoker = self._actor_and_invoker()
                        search = invoker.invoke_company_search(query=query)
                        _validate_company_search(search, query)
                    except Exception:
                        self._json(502, {"error": "search_backend_unavailable"}, route="company_search")
                        return
                    finally:
                        app.request_slots.release()
                    self._json(200, search, route="company_search")
                    return
                if parsed.path != "/api/v1/entity-graph":
                    self._json(404, {"error": "not_found"}, route="unknown")
                    return
                try:
                    request = _parse_graph_query(parsed.query)
                except ValueError as exc:
                    self._json(400, {"error": str(exc)}, route="entity_graph")
                    return
                if not app.request_slots.acquire(blocking=False):
                    self._json(503, {"error": "graph_backend_busy"}, route="entity_graph")
                    return
                try:
                    _actor, invoker = self._actor_and_invoker()
                    graph = invoker.invoke(**request)
                except Exception:
                    # Never reflect exception text: SDK errors may include child env,
                    # filesystem paths, user input or server diagnostics.
                    self._json(502, {"error": "graph_backend_unavailable"}, route="entity_graph")
                    return
                finally:
                    app.request_slots.release()
                try:
                    _validate_graph_view(graph)
                except (TypeError, ValueError):
                    self._json(502, {"error": "graph_backend_invalid"}, route="entity_graph")
                    return
                self._json(200, graph, route="entity_graph")

        return Handler


def _one(params: dict[str, list[str]], name: str, default: str = "") -> str:
    values = params.get(name, [])
    if len(values) > 1:
        raise ValueError("invalid_query")
    return values[0] if values else default


def _parse_graph_query(query: str) -> dict:
    try:
        params = parse_qs(query, keep_blank_values=True, max_num_fields=20, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("invalid_query") from exc
    if not set(params).issubset(ALLOWED_QUERY):
        raise ValueError("invalid_query")
    entity = _one(params, "entity").strip()
    if not entity or len(entity) > MAX_ENTITY_LENGTH or any(ord(char) < 32 for char in entity):
        raise ValueError("invalid_entity")
    entity_type = _one(params, "entity_type", "company").strip()
    if entity_type != "company":
        raise ValueError("invalid_entity_type")
    depth_text = _one(params, "depth", "1")
    if depth_text != "1":
        raise ValueError("invalid_depth")
    include_text = _one(params, "include").strip()
    include = None
    if include_text:
        include = [item.strip() for item in include_text.split(",")]
        if len(include) > MAX_INCLUDE_ITEMS or not set(include).issubset(SUPPORTED_INCLUDE):
            raise ValueError("invalid_include")
    return {"entity": entity, "entity_type": entity_type, "depth": 1, "include": include}


def _parse_search_query(query: str) -> str:
    try:
        params = parse_qs(query, keep_blank_values=True, max_num_fields=2, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("invalid_query") from exc
    if set(params) != ALLOWED_SEARCH_QUERY:
        raise ValueError("invalid_query")
    value = _one(params, "q").strip()
    if len(value) < 2 or len(value) > MAX_SEARCH_QUERY_LENGTH or any(ord(char) < 32 for char in value):
        raise ValueError("invalid_search_query")
    return value


def _parse_guided_query(query: str) -> dict:
    try:
        params = parse_qs(query, keep_blank_values=True, max_num_fields=3, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("invalid_query") from exc
    if set(params) != ALLOWED_GUIDED_QUERY:
        raise ValueError("invalid_query")
    intent = _one(params, "intent").strip()
    entity = _one(params, "entity").strip()
    if intent not in GUIDED_INTENTS:
        raise ValueError("invalid_intent")
    if not entity or len(entity) > MAX_ENTITY_LENGTH or any(ord(char) < 32 for char in entity):
        raise ValueError("invalid_entity")
    return {"intent": intent, "entity": entity}


def _validate_company_search(value: object, query: str) -> None:
    if not isinstance(value, dict) or value.get("status") != "ok" or value.get("query") != query:
        raise ValueError("invalid company search")
    items = value.get("items")
    if not isinstance(items, list) or len(items) > 8:
        raise ValueError("invalid company search")
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "company":
            raise ValueError("invalid company search")
        if not all(isinstance(item.get(key), str) and item[key] for key in ("entity_id", "label")):
            raise ValueError("invalid company search")


def _validate_dashboard(value: object) -> None:
    if not isinstance(value, dict) or value.get("contract") != "saleswiki.dashboard-view" or value.get("version") != 1:
        raise ValueError("invalid dashboard")
    if value.get("access") != "allowed" or not isinstance(value.get("synthetic"), bool):
        raise ValueError("invalid dashboard")
    if value.get("history_status") not in {"available", "insufficient-history"}:
        raise ValueError("invalid dashboard")
    for key in ("risk", "coverage", "signals"):
        if not isinstance(value.get(key), list) or len(value[key]) > 12:
            raise ValueError("invalid dashboard")
    for item in value["risk"]:
        if not isinstance(item, dict) or not isinstance(item.get("entity_id"), str) or not isinstance(item.get("history"), list):
            raise ValueError("invalid dashboard")


def _validate_guided_answer(value: object, intent: str) -> None:
    if not isinstance(value, dict) or value.get("intent") != intent:
        raise ValueError("invalid guided answer")
    _validate_account_brief(value)


def _parse_import_request(headers, stream) -> dict:
    """Accept only a small JSON review summary; raw files never cross this BFF."""
    content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    try:
        length = int(headers.get("Content-Length", ""))
    except ValueError as exc:
        raise ValueError("invalid_import") from exc
    if content_type != "application/json" or length < 2 or length > MAX_IMPORT_BODY_BYTES:
        raise ValueError("invalid_import")
    try:
        payload = json.loads(stream.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_import") from exc
    if not isinstance(payload, dict) or set(payload) != {"target", "summary"}:
        raise ValueError("invalid_import")
    target, summary = payload.get("target"), payload.get("summary")
    if not isinstance(target, str) or not isinstance(summary, str):
        raise ValueError("invalid_import")
    target, summary = target.strip(), " ".join(summary.split())
    if (
        not target or not summary or len(target) > MAX_IMPORT_TARGET_LENGTH
        or len(summary) > MAX_IMPORT_SUMMARY_LENGTH
        or any(ord(char) < 32 for char in target)
    ):
        raise ValueError("invalid_import")
    return {"target": target, "summary": summary}


def _validate_import_proposal(value: object) -> None:
    if not isinstance(value, dict) or value.get("status") != "draft":
        raise ValueError("invalid import proposal")
    proposal_id = value.get("proposal_id")
    if not isinstance(proposal_id, str) or not proposal_id.startswith("proposal-") or len(proposal_id) > 40:
        raise ValueError("invalid import proposal")


def _parse_update_proposal(headers, stream) -> dict:
    content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    try:
        length = int(headers.get("Content-Length", ""))
    except ValueError as exc:
        raise ValueError("invalid_update") from exc
    if content_type != "application/json" or length < 2 or length > MAX_UPDATE_BODY_BYTES:
        raise ValueError("invalid_update")
    try:
        payload = json.loads(stream.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_update") from exc
    if not isinstance(payload, dict) or set(payload) != {"target", "note"}:
        raise ValueError("invalid_update")
    target, note = payload.get("target"), payload.get("note")
    if not isinstance(target, str) or not isinstance(note, str):
        raise ValueError("invalid_update")
    target, note = target.strip(), " ".join(note.split())
    if not target or len(target) > MAX_IMPORT_TARGET_LENGTH or not note or len(note) > MAX_UPDATE_NOTE_LENGTH:
        raise ValueError("invalid_update")
    return {"target": target, "note": note}


def _parse_demo_persona(headers, stream) -> str:
    """Accept a fixture id, never a role, scope, or arbitrary identity claim."""
    content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    try:
        length = int(headers.get("Content-Length", ""))
    except ValueError as exc:
        raise ValueError("invalid_demo_persona") from exc
    if content_type != "application/json" or length < 2 or length > 160:
        raise ValueError("invalid_demo_persona")
    try:
        payload = json.loads(stream.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_demo_persona") from exc
    actor_id = payload.get("actor_id") if isinstance(payload, dict) and set(payload) == {"actor_id"} else None
    if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id.strip()) > MAX_SESSION_ACTOR_LENGTH:
        raise ValueError("invalid_demo_persona")
    return actor_id.strip()


def _validate_account_brief(value: object) -> None:
    if not isinstance(value, dict) or value.get("access") not in {"allowed", "sanitized", "blocked", "not-found", "ambiguous"}:
        raise ValueError("invalid account brief")
    if not isinstance(value.get("conclusion"), str) or not isinstance(value.get("citations"), list):
        raise ValueError("invalid account brief")


def _parse_review_decision(headers, stream) -> dict:
    content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    try:
        length = int(headers.get("Content-Length", ""))
    except ValueError as exc:
        raise ValueError("invalid_review") from exc
    if content_type != "application/json" or length < 2 or length > MAX_REVIEW_BODY_BYTES:
        raise ValueError("invalid_review")
    try:
        payload = json.loads(stream.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_review") from exc
    if not isinstance(payload, dict) or set(payload) != {"proposal_id", "action", "reason"}:
        raise ValueError("invalid_review")
    proposal_id, action, reason = payload.get("proposal_id"), payload.get("action"), payload.get("reason")
    if not all(isinstance(value, str) for value in (proposal_id, action, reason)):
        raise ValueError("invalid_review")
    proposal_id, action, reason = proposal_id.strip(), action.strip(), " ".join(reason.split())
    if (
        not proposal_id.startswith("proposal-") or len(proposal_id) > MAX_PROPOSAL_ID_LENGTH
        or action not in {"approve", "reject"} or len(reason) > MAX_REJECTION_REASON_LENGTH
        or (action == "reject" and not reason)
    ):
        raise ValueError("invalid_review")
    return {"proposal_id": proposal_id, "action": action, "reason": reason}


def _validate_review_queue(value: object) -> None:
    if not isinstance(value, dict) or value.get("access") not in {"allowed", "blocked"}:
        raise ValueError("invalid review queue")
    if not isinstance(value.get("can_decide"), bool) or not isinstance(value.get("items"), list):
        raise ValueError("invalid review queue")
    for item in value["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("proposal_id"), str) or item.get("status") not in {"draft", "approved"}:
            raise ValueError("invalid review queue")


def _validate_review_decision(value: object) -> None:
    if not isinstance(value, dict) or value.get("status") not in {"approved", "rejected", "blocked", "not-found"}:
        raise ValueError("invalid review result")
    if not isinstance(value.get("proposal_id"), str):
        raise ValueError("invalid review result")


def _validate_graph_view(graph: object) -> None:
    if not isinstance(graph, dict):
        raise TypeError("invalid GraphView")
    if graph.get("contract") != "saleswiki.graph-view" or graph.get("version") != 1:
        raise ValueError("invalid GraphView contract")
    if graph.get("access") not in {
        "allowed", "sanitized", "aggregated", "blocked", "not-found", "ambiguous"
    }:
        raise ValueError("invalid GraphView access")
    required_types = {
        "summary": dict,
        "nodes": list,
        "edges": list,
        "evidence": list,
        "restricted": list,
        "missing": list,
    }
    if any(not isinstance(graph.get(key), expected) for key, expected in required_types.items()):
        raise ValueError("invalid GraphView required field")
    if any(not isinstance(item, str) for key in ("restricted", "missing") for item in graph[key]):
        raise ValueError("invalid GraphView notice")
    for key, limit in (("nodes", MAX_NODES), ("edges", MAX_EDGES), ("evidence", MAX_EVIDENCE)):
        value = graph.get(key)
        if len(value) > limit:
            raise ValueError("invalid GraphView records")
        if any(not isinstance(item, dict) for item in value):
            raise ValueError("invalid GraphView record")
    try:
        GraphProjector._validate(graph)
    except (GraphProjectionError, KeyError, TypeError, IndexError) as exc:
        raise ValueError("invalid GraphView invariants") from exc
    try:
        encoded = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("GraphView must be JSON serializable") from exc
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("GraphView response is too large")


def _validate_answer(answer: object) -> None:
    if not isinstance(answer, dict):
        raise TypeError("invalid Answer")
    required = {"title": str, "access": str, "conclusion": str, "sections": list, "citations": list,
                "restricted": list, "confidence": str, "freshness": str, "as_of": str, "next_action": str,
                "missing": list, "text": str}
    if any(not isinstance(answer.get(key), value_type) for key, value_type in required.items()):
        raise ValueError("invalid Answer fields")
    if answer["access"] not in {"allowed", "sanitized", "aggregated", "blocked", "not-found", "ambiguous"}:
        raise ValueError("invalid Answer access")
    if any(not isinstance(item, dict) for item in answer["sections"] + answer["citations"]):
        raise ValueError("invalid Answer record")
    if any(not isinstance(item, str) for key in ("restricted", "missing") for item in answer[key]):
        raise ValueError("invalid Answer notice")
    if len(json.dumps(answer, ensure_ascii=False).encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("Answer response is too large")


def _validate_origin(origin: str) -> str:
    if not origin or any(char in origin for char in "\r\n"):
        raise ConfigError("workbench.allowed_origins contains an invalid origin")
    parsed = urlsplit(origin)
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ConfigError("workbench.allowed_origins contains an invalid port") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or (parsed_port is not None and not 1 <= parsed_port <= 65535)
    ):
        raise ConfigError("workbench.allowed_origins must contain exact http(s) origins")
    return origin.rstrip("/")


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def build_app_from_settings(
    settings: RuntimeSettings, env: Mapping[str, str] | None = None
) -> WorkbenchApp:
    env = env if env is not None else os.environ
    if not settings.workbench.enabled:
        raise ConfigError("workbench is disabled in runtime config")
    if settings.profile != "demo" or settings.workbench.identity_provider != "fixture":
        raise ConfigError("Workbench BFF currently requires demo profile with fixture identity")
    if settings.workbench.mcp_transport != "stdio":
        raise ConfigError("Workbench BFF currently requires stdio MCP transport")
    if not _is_loopback_host(settings.workbench.host):
        raise ConfigError("non-loopback Workbench BFF bind is disabled; use the UI development proxy for a LAN demo")
    vault_root = Path(settings.vault.root or DEFAULT_VAULT).resolve()
    runtime_dir = Path(settings.vault.runtime or DEFAULT_RUNTIME).resolve()
    vault_guard.require_demo_vault(vault_root, context="Workbench BFF (fixture identity)")
    # Unlike the generic fixture gateway, this bridge is explicitly demo-only:
    # even the generic emergency production override must not broaden its scope.
    if not vault_guard.is_demo_vault(vault_root):
        raise ConfigError("Workbench BFF requires a demo/synthetic vault")
    identity_config = config.identity_config()
    actor = FixtureIdentityProvider.from_env(identity_config, env=env).resolve()
    fixture_users = identity_config.get("providers", {}).get("fixture", {}).get("users", [])
    personas = tuple(
        DemoPersona(
            id=user["id"], name=user.get("name", user["id"]), role=user["role"], team=user.get("team", "")
        )
        for user in fixture_users
        if isinstance(user, dict) and isinstance(user.get("id"), str) and isinstance(user.get("role"), str)
    )
    persona_index = {persona.id: persona for persona in personas}
    sessions = DemoSessionStore(actor.id, persona_index)
    return WorkbenchApp(
        invoker=McpGraphInvoker(
            actor.id, vault_root, runtime_dir,
            timeout_seconds=settings.workbench.timeout_seconds,
        ),
        invoker_factory=lambda actor_id: McpGraphInvoker(
            actor_id, vault_root, runtime_dir, timeout_seconds=settings.workbench.timeout_seconds
        ),
        demo_sessions=sessions,
        demo_personas=personas,
        allow_fixture_persona_switching=settings.workbench.allow_fixture_persona_switching,
        allowed_origins=tuple(_validate_origin(item) for item in settings.workbench.allowed_origins),
        request_slots=threading.BoundedSemaphore(settings.workbench.max_concurrent_requests),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the demo-only SalesWiki Workbench BFF")
    parser.add_argument("--config", help="Runtime TOML (or set SALESWIKI_CONFIG)")
    args = parser.parse_args()
    settings = load_runtime_settings(args.config, allow_legacy=False)
    app = build_app_from_settings(settings)
    ThreadingHTTPServer(
        (settings.workbench.host, settings.workbench.port), app.handler_class()
    ).serve_forever()


if __name__ == "__main__":
    main()
