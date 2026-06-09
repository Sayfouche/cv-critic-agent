"""FastAPI server exposing the CV Critic Agent over HTTP + SSE.

Core endpoints (runs + sources):
    POST   /api/runs                         start a new run (mock or real)
    GET    /api/runs                         list active/recent runs
    GET    /api/runs/{run_id}                full state snapshot
    GET    /api/runs/{run_id}/events         SSE stream of lifecycle events
    GET    /api/runs/{run_id}/reports/{slug} read a generated report (markdown)
    GET    /api/sources                      list portfolio source snapshots
    GET    /api/sources/{name}               read a source snapshot file
    GET    /api/graph                        static agent dependency topology
    GET    /api/health                       liveness probe

Phase 5 — Access gate (Sprint 4+):
    POST   /api/access-requests              submit access request
    GET    /api/access-requests/{id}/status  public status poll
    GET    /api/access-requests/{id}/decide  owner HMAC decision link
    POST   /api/telegram/webhook             Telegram bot webhook
    POST   /api/admin/login                  send admin magic link
    GET    /api/admin/session/{token}        redeem magic link
    GET    /api/admin/requests               list requests (admin)
    PATCH  /api/admin/requests/{id}          approve/reject/revoke (admin)

Real-mode runs require `CV_CRITIC_API_TOKEN` env var to be set on the server;
clients pass it as `?token=...` or `X-API-Token` header. Mock runs are public.
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from cv_critic_agent.events import AGENT_GRAPH
from cv_critic_agent.paths import project_root
from cv_critic_agent.run_manager import RunManager
from cv_critic_agent.sources import GLOBAL_SOURCES

_manager = RunManager()


# ── Phase 5 lifespan: wire access-gate dependencies ──────────────────────────

def _setup_access_gate(app: FastAPI) -> None:  # noqa: F811
    """Read env vars and populate app.state with access-gate dependencies.

    Called once at startup. All values default to empty strings / None so
    the server starts cleanly even when Phase 5 vars are not configured;
    in that case the Phase 5 endpoints return 503.
    """
    hmac_key = os.environ.get("HMAC_KEY", "")
    fernet_key = os.environ.get("FERNET_KEY", "")

    app.state.hmac_secret = hmac_key.encode() if hmac_key else b""
    app.state.turnstile_secret = os.environ.get("TURNSTILE_SECRET", "")
    app.state.tg_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    app.state.tg_owner_chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")
    app.state.resend_api_key = os.environ.get("RESEND_API_KEY", "")
    app.state.resend_from = os.environ.get(
        "RESEND_FROM_ADDRESS", "noreply@cv-critic.saifallah.dev"
    )
    app.state.owner_email = os.environ.get("OWNER_EMAIL", "")
    app.state.base_url = os.environ.get("CV_CRITIC_BASE_URL", "").rstrip("/")
    app.state.ui_url = os.environ.get("CV_CRITIC_UI_URL", "").rstrip("/")
    app.state.cleanup_secret = os.environ.get("CV_CRITIC_CLEANUP_SECRET", "")
    # Override-able in tests — never set from env (factory objects are not strings).
    if not hasattr(app.state, "captcha_http_factory"):
        app.state.captcha_http_factory = None
    if not hasattr(app.state, "notifier_http_factory"):
        app.state.notifier_http_factory = None

    if fernet_key:
        from cv_critic_agent.access_requests.store import AccessRequestStore

        store_path = Path(
            os.environ.get("ACCESS_REQUESTS_DIR", "data/access_requests")
        )
        app.state.ar_store = AccessRequestStore(store_path, fernet_key.encode())
    else:
        app.state.ar_store = None

    from cv_critic_agent.budget.tracker import BudgetTracker

    daily_cap = int(os.environ.get("MAX_TOKENS_PER_DAY", "200000"))
    budget_dir = Path(os.environ.get("BUDGET_DIR", "data/budget"))
    app.state.budget_tracker = BudgetTracker(budget_dir, daily_cap_tokens=daily_cap)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    _setup_access_gate(app)
    yield


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(title="CV Critic Agent API", version="0.1.0", lifespan=lifespan)

# CORS — UI is hosted on a different origin in production.
_allowed_origins = os.environ.get("CV_CRITIC_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# ── Rate limiter (slowapi) ────────────────────────────────────────────────────
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from cv_critic_agent.security.limiter import limiter  # noqa: E402

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Phase 5 routers ───────────────────────────────────────────────────────────
from cv_critic_agent.access_requests.router import router as ar_router  # noqa: E402
from cv_critic_agent.admin.router import router as admin_router  # noqa: E402
from cv_critic_agent.cron_router import router as cron_router  # noqa: E402
from cv_critic_agent.telegram_webhook_router import router as tg_router  # noqa: E402

app.include_router(ar_router)
app.include_router(admin_router)
app.include_router(tg_router)
app.include_router(cron_router)


# ── Helpers ──────────────────────────────────────────────────────────────────
from cv_critic_agent.access_requests.models import (  # noqa: E402
    InvalidTransition,
    IpBindingMismatch,
    QuotaExceeded,
    SessionExpired,
)
from cv_critic_agent.security.limiter import _client_ip  # noqa: E402
from cv_critic_agent.security.session import (  # noqa: E402
    InvalidSessionToken,
    SessionIpMismatch,
    SessionNotApproved,
    SessionQuotaExceeded,
    verify_session,
)


def _build_budget_callback(state: Any):
    """Closure that records a real run's output-token estimate + alerts.

    Returns None when notifier or tracker is not configured — the worker
    thread then simply skips post-run accounting. The callback is sync
    because the run worker is a thread; we open a one-shot event loop via
    ``asyncio.run`` and swallow any error (fail-soft notifier rule).
    """
    tracker = getattr(state, "budget_tracker", None)
    bot_token = getattr(state, "tg_bot_token", "")
    owner_chat_id = getattr(state, "tg_owner_chat_id", "")
    factory = getattr(state, "notifier_http_factory", None)
    if tracker is None or not bot_token or not owner_chat_id:
        return None

    from cv_critic_agent.budget.wiring import record_real_run

    def callback(n_tokens: int) -> None:
        try:
            asyncio.run(
                record_real_run(
                    tracker,
                    n_tokens,
                    bot_token=bot_token,
                    owner_chat_id=owner_chat_id,
                    http_client_factory=factory,
                )
            )
        except Exception:  # pragma: no cover — fail-soft
            return

    return callback


def _consume_real_run_or_degrade(
    request: Request, session_token: str | None
) -> tuple[bool, bool]:
    """Gate a real-mode run.

    Returns ``(mock_to_use, degraded)``:
        - ``(False, False)`` — session valid, run real, slot consumed.
        - ``(True, True)``  — budget cap hit, degraded silently to mock,
            no slot consumed.

    Raises ``HTTPException`` for every other failure (missing config,
    invalid token, not approved, IP mismatch, quota exhausted).
    """
    ar_store = getattr(request.app.state, "ar_store", None)
    budget_tracker = getattr(request.app.state, "budget_tracker", None)
    hmac_secret = getattr(request.app.state, "hmac_secret", b"")
    if ar_store is None or budget_tracker is None or not hmac_secret:
        raise HTTPException(
            status_code=503,
            detail="Real runs are disabled on this server.",
        )
    if not session_token:
        raise HTTPException(status_code=401, detail="session_token required.")

    client_ip = _client_ip(request)
    try:
        ar = verify_session(session_token, client_ip, hmac_secret, ar_store)
    except InvalidSessionToken:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    except SessionNotApproved:
        raise HTTPException(status_code=403, detail="Session not approved.")
    except SessionIpMismatch:
        raise HTTPException(
            status_code=403, detail="Session bound to a different IP."
        )
    except SessionQuotaExceeded:
        raise HTTPException(status_code=403, detail="Quota exhausted.")

    if budget_tracker.should_degrade():
        return True, True

    try:
        ar_store.atomic_consume_run(ar.id, client_ip)
    except (
        InvalidTransition,
        IpBindingMismatch,
        QuotaExceeded,
        SessionExpired,
    ):
        raise HTTPException(status_code=403, detail="Session no longer valid.")

    return False, False


def _safe_source_path(name: str) -> Path:
    if "/" in name or ".." in name or name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid source name.")
    relative = f"sources/{name}"
    if relative not in GLOBAL_SOURCES:
        raise HTTPException(status_code=404, detail="Unknown source file.")
    return project_root() / relative


def _safe_report_path(run_dir: str, slug: str) -> Path:
    allowed = {"global", "printable-cv", "strategy", "summary"}
    if slug not in allowed:
        raise HTTPException(status_code=400, detail="Invalid report slug.")
    target = Path(run_dir) / f"{slug}.md"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Report not yet generated.")
    return target


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph")
async def graph() -> dict[str, Any]:
    return {"agents": AGENT_GRAPH}


@app.get("/api/sources")
async def list_sources() -> dict[str, Any]:
    items = []
    for relative in GLOBAL_SOURCES:
        absolute = project_root() / relative
        name = Path(relative).name
        items.append({
            "name": name,
            "path": relative,
            "size": absolute.stat().st_size if absolute.exists() else 0,
            "exists": absolute.exists(),
        })
    return {"sources": items}


@app.get("/api/sources/{name}", response_class=PlainTextResponse)
async def get_source(name: str) -> str:
    return _safe_source_path(name).read_text(encoding="utf-8")


@app.post("/api/runs")
async def create_run(
    payload: dict[str, Any],
    request: Request,
    token_q: str | None = Query(default=None, alias="token"),
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> dict[str, Any]:
    mock = bool(payload.get("mock", True))
    demo_delay_ms = int(payload.get("demo_delay_ms", 0) or 0)
    degraded = False
    budget_callback = None
    if not mock:
        session_token = x_session_token or token_q
        mock, degraded = _consume_real_run_or_degrade(request, session_token)
        if not mock:
            budget_callback = _build_budget_callback(request.app.state)
    state = _manager.create_run(
        mock=mock, demo_delay_ms=demo_delay_ms, budget_callback=budget_callback
    )
    return {
        "run_id": state.run_id,
        "mock": state.mock,
        "status": state.status,
        "degraded": degraded,
    }


@app.get("/api/runs")
async def list_runs() -> dict[str, Any]:
    return {"runs": _manager.list_runs()}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    state = _manager.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown run id.")
    return {
        "run_id": state.run_id,
        "status": state.status,
        "mock": state.mock,
        "provider": state.provider,
        "model": state.model,
        "started_at": state.started_at,
        "run_dir": state.run_dir,
        "error": state.error,
        "events": state.events,
    }


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request) -> StreamingResponse:
    state = _manager.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown run id.")

    queue = _manager.subscribe(run_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Unknown run id.")

    async def event_generator():
        # Replay buffered events first so a late subscriber sees the timeline.
        for event in list(state.events):
            yield f"data: {json.dumps(event)}\n\n"

        while True:
            if await request.is_disconnected():
                break
            # Use to_thread for the blocking queue.get to keep the event loop free.
            item = await asyncio.to_thread(_manager.drain, queue, 1.0)
            if item is None:
                yield ": keep-alive\n\n"
                continue
            if _manager.is_sentinel(item):
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/runs/{run_id}/reports/{slug}", response_class=PlainTextResponse)
async def get_report(run_id: str, slug: str) -> str:
    state = _manager.get(run_id)
    if state is None or state.run_dir is None:
        raise HTTPException(status_code=404, detail="Run not started or finished.")
    return _safe_report_path(state.run_dir, slug).read_text(encoding="utf-8")


def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    import uvicorn

    uvicorn.run("cv_critic_agent.api:app", host=host, port=port, reload=reload)
