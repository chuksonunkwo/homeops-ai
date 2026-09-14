from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .config import BASE_DIR, DATABASE_URL, DB_PATH, MCP_ALLOWED_HOSTS, MCP_ALLOWED_ORIGINS
from .conversation import HomeOpsConversation
from .engine import HomeOpsEngine
from .store import Store

store = Store(DB_PATH, database_url=DATABASE_URL)
engine = HomeOpsEngine(store)
conversation = HomeOpsConversation(engine)
STATIC_DIR = BASE_DIR / "static"

MCP_AVAILABLE = False
mcp = None
mcp_app = None
mcp_import_error = ""

try:
    from mcp.server import MCPServer
    from mcp.server.transport_security import TransportSecuritySettings

    mcp = MCPServer("HomeOps AI")

    @mcp.tool()
    def create_service_request(
        issue: str,
        category: str = "auto",
        location: str = "Home",
        max_budget: float | None = None,
    ) -> dict[str, Any]:
        """Create a governed home-service request from the customer's problem statement."""
        return engine.create_service_request(issue, category, location, max_budget)

    @mcp.tool()
    def diagnose_service_request(job_id: str) -> dict[str, Any]:
        """Classify the request and stop normal sourcing when emergency language is detected."""
        return engine.diagnose_service_request(job_id)

    @mcp.tool()
    def search_providers(job_id: str) -> list[dict[str, Any]]:
        """Find verified providers relevant to a service request."""
        return engine.search_providers(job_id)

    @mcp.tool()
    def request_quotes(job_id: str) -> list[dict[str, Any]]:
        """Request comparable quotes for a service request."""
        return engine.request_quotes(job_id)

    @mcp.tool()
    def compare_quotes(job_id: str) -> dict[str, Any]:
        """Score quotes on transparent price, rating and response-speed criteria."""
        return engine.compare_quotes(job_id)

    @mcp.tool()
    def approve_provider(job_id: str, provider_name_or_id: str) -> dict[str, Any]:
        """Record the customer's explicit provider approval and commercial baseline."""
        return engine.approve_provider(job_id, provider_name_or_id)

    @mcp.tool()
    def schedule_service(job_id: str, appointment_window: str = "") -> dict[str, Any]:
        """Schedule an approved provider using the quoted window or an explicit replacement window."""
        return engine.schedule_service(job_id, appointment_window or None)

    @mcp.tool()
    def get_service_job(job_id: str) -> dict[str, Any]:
        """Return current state, quotes, invoice and audit events for a service job."""
        return engine.get_job(job_id)

    @mcp.tool()
    def record_service_completion(job_id: str, completion_note: str = "Service completed") -> dict[str, Any]:
        """Record that the selected provider completed the service."""
        return engine.record_service_completion(job_id, completion_note)

    @mcp.tool()
    def submit_and_review_invoice(
        job_id: str,
        total: float,
        callout: float = 0,
        service: float = 0,
        materials: float = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        """Compare an invoice to the approved quote and hold unapproved cost increases."""
        return engine.submit_invoice(job_id, total, callout, service, materials, notes)

    @mcp.tool()
    def challenge_invoice_variance(job_id: str, note: str = "Request supplier justification") -> dict[str, Any]:
        """Keep payment on hold and record a request for supplier justification of the variance."""
        return engine.challenge_invoice_variance(job_id, note)

    @mcp.tool()
    def close_service_job(job_id: str, approve_variance: bool = False) -> dict[str, Any]:
        """Close a job only after invoice controls pass or a variance is explicitly approved."""
        return engine.close_job(job_id, approve_variance)

    security = TransportSecuritySettings(
        allowed_hosts=MCP_ALLOWED_HOSTS,
        allowed_origins=MCP_ALLOWED_ORIGINS,
    )
    # The mounted public endpoint becomes /mcp because streamable_http_app defaults to /mcp.
    mcp_app = mcp.streamable_http_app(
        transport_security=security,
        stateless_http=True,
        json_response=True,
    )
    MCP_AVAILABLE = True
except Exception as exc:  # pragma: no cover - exercised only when MCP dependency is unavailable
    mcp_import_error = f"{exc.__class__.__name__}: {exc}"


def _json(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status)


async def homepage(_: Request):
    return FileResponse(STATIC_DIR / "index.html")


async def health(_: Request):
    bedrock = engine.reviewer.status()
    return _json(
        {
            "status": "ok",
            "app": "HomeOps AI",
            "version": "0.4.1",
            "storage_backend": store.backend,
            "mcp_available": MCP_AVAILABLE,
            "mcp_endpoint": "/mcp" if MCP_AVAILABLE else None,
            "mcp_error": None if MCP_AVAILABLE else mcp_import_error or "MCP package not installed",
            "bedrock": {
                "enabled": bedrock["enabled"],
                "configured": bedrock["configured"],
                "region": bedrock["region"],
                "model_id": bedrock["model_id"],
            },
        }
    )


async def bedrock_status(_: Request):
    return _json(engine.reviewer.status())


async def bedrock_test(_: Request):
    # Explicit only: this makes a real, billable low-token Bedrock call.
    result = await asyncio.to_thread(engine.reviewer.test_connection)
    return _json(result, 200 if result.get("success") else 400)


async def demo_reset(_: Request):
    store.reset()
    return _json({"success": True, "message": "Demo state reset."})


async def get_job(request: Request):
    try:
        return _json(engine.get_job(request.path_params["job_id"]))
    except KeyError as exc:
        return _json({"success": False, "error": str(exc)}, 404)


async def list_tools(_: Request):
    return _json(
        {
            "mcp_available": MCP_AVAILABLE,
            "tools": [
                "create_service_request",
                "diagnose_service_request",
                "search_providers",
                "request_quotes",
                "compare_quotes",
                "approve_provider",
                "schedule_service",
                "get_service_job",
                "record_service_completion",
                "submit_and_review_invoice",
                "challenge_invoice_variance",
                "close_service_job",
            ],
        }
    )


async def demo_scenarios(_: Request):
    return _json(
        {
            "scenarios": [
                {
                    "id": "hvac-golden",
                    "label": "AC golden flow",
                    "message": "My AC isn't cooling. Handle it.",
                    "purpose": "Sourcing, quote evaluation, scheduling and invoice variance control",
                },
                {
                    "id": "plumbing",
                    "label": "Plumbing",
                    "message": "My kitchen pipe is leaking. Keep it under $90.",
                    "purpose": "Budget-aware sourcing and provider selection",
                },
                {
                    "id": "emergency",
                    "label": "Safety stop",
                    "message": "There is smoke coming from my air conditioner.",
                    "purpose": "Emergency language blocks normal automated sourcing",
                },
            ]
        }
    )


async def chat(request: Request):
    try:
        payload = await request.json()
        message = str(payload.get("message", "")).strip()
        job_id = payload.get("job_id")
        result = await asyncio.to_thread(conversation.handle, message, job_id)
        return _json(result)
    except (ValueError, KeyError) as exc:
        return _json({"success": False, "error": str(exc)}, 400)
    except json.JSONDecodeError:
        return _json({"success": False, "error": "Invalid JSON body"}, 400)


routes = [
    Route("/", homepage, methods=["GET"]),
    Route("/health", health, methods=["GET"]),
    Route("/api/bedrock/status", bedrock_status, methods=["GET"]),
    Route("/api/bedrock/test", bedrock_test, methods=["POST"]),
    Route("/api/demo/reset", demo_reset, methods=["POST"]),
    Route("/api/demo/scenarios", demo_scenarios, methods=["GET"]),
    Route("/api/chat", chat, methods=["POST"]),
    Route("/api/jobs/{job_id}", get_job, methods=["GET"]),
    Route("/api/tools", list_tools, methods=["GET"]),
    Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
]

if MCP_AVAILABLE and mcp_app is not None:
    routes.append(Mount("/", app=mcp_app))
else:
    async def mcp_missing(_: Request):
        return _json(
            {
                "error": "MCP runtime is not installed in this environment.",
                "detail": mcp_import_error or "Install project dependencies to enable the MCP endpoint.",
            },
            503,
        )
    routes.append(Route("/mcp", mcp_missing, methods=["GET", "POST", "DELETE"]))


@asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[None]:
    if MCP_AVAILABLE and mcp is not None:
        async with mcp.session_manager.run():
            yield
    else:
        yield


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=MCP_ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Last-Event-ID",
            "Mcp-Method",
            "Mcp-Name",
            "Mcp-Protocol-Version",
            "Mcp-Session-Id",
        ],
        expose_headers=["Mcp-Session-Id"],
    )
]

app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)
