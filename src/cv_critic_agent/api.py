"""FastAPI server exposing the CV Critic Agent over HTTP + SSE.

Endpoints:
    POST   /api/runs                         start a new run (mock or real)
    GET    /api/runs                         list active/recent runs
    GET    /api/runs/{run_id}                full state snapshot
    GET    /api/runs/{run_id}/events         SSE stream of lifecycle events
    GET    /api/runs/{run_id}/reports/{slug} read a generated report (markdown)
    GET    /api/sources                      list portfolio source snapshots
    GET    /api/sources/{name}               read a source snapshot file
    GET    /api/graph                        static agent dependency topology
    GET    /api/health                       liveness probe

Real-mode runs require `CV_CRITIC_API_TOKEN` env var to be set on the server;
clients pass it as `?token=...` or `X-API-Token` header. Mock runs are public.
"""
from __future__ import annotations

import asyncio
import json
import os
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

app = FastAPI(title="CV Critic Agent API", version="0.1.0")

# CORS — UI is hosted on a different origin in production.
_allowed_origins = os.environ.get("CV_CRITIC_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _require_auth_for_real(mock: bool, token_query: str | None, token_header: str | None) -> None:
    if mock:
        return
    expected = os.environ.get("CV_CRITIC_API_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Real runs are disabled on this server (CV_CRITIC_API_TOKEN not set).",
        )
    provided = token_header or token_query
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")


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
    token_q: str | None = Query(default=None, alias="token"),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
) -> dict[str, Any]:
    mock = bool(payload.get("mock", True))
    demo_delay_ms = int(payload.get("demo_delay_ms", 0) or 0)
    _require_auth_for_real(mock, token_q, x_api_token)
    state = _manager.create_run(mock=mock, demo_delay_ms=demo_delay_ms)
    return {"run_id": state.run_id, "mock": state.mock, "status": state.status}


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
