from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Path as ApiPath, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from kisansathi_auth.csrf import CsrfTokenCodec
from kisansathi_auth.session import SessionCodec

from .auth import HarnessAuthError, authenticate_request
from .event_store import EventStore
from .orchestrator import Orchestrator, OrchestratorError
from .protocol import EventEnvelope, ResumeSnapshot
from .provider_config import ProviderConfig, ProviderConfigError
from .provider_runtime import ProviderRuntime
from .providers.fake import FakeProvider
from .sessions import HarnessSession, SessionManager, SessionOwnershipError


SESSION_COOKIE = "kisansathi_session"
CSRF_COOKIE = "kisansathi_csrf"
DEFAULT_DEV_SECRET = "development-session-secret-change-me-32"
DEFAULT_CSRF_SECRET = "development-csrf-secret-change-me-32"


@dataclass(frozen=True, slots=True)
class HarnessSettings:
    environment: str
    session_secret: str
    csrf_secret: str
    session_kid: str
    session_ttl_seconds: int
    csrf_ttl_seconds: int
    provider_configured: bool
    provider_error: str | None
    event_store_path: Path | None

    @classmethod
    def from_env(cls) -> "HarnessSettings":
        environment = os.getenv("KISANSATHI_ENV", "development").strip().lower()
        session_secret = os.getenv("KISANSATHI_SESSION_SECRET", "") or DEFAULT_DEV_SECRET
        csrf_secret = os.getenv("KISANSATHI_CSRF_SECRET", "") or DEFAULT_CSRF_SECRET
        if len(session_secret) < 16 or len(csrf_secret) < 16:
            raise RuntimeError("Harness session and CSRF secrets must be at least 16 bytes.")
        model = os.getenv("KISANSATHI_LLM_MODEL", "").strip()
        provider_error: str | None = None
        try:
            ProviderConfig.from_env()
        except ProviderConfigError as exc:
            provider_error = str(exc)
        provider_configured = bool(model) and provider_error is None
        return cls(
            environment=environment,
            session_secret=session_secret,
            csrf_secret=csrf_secret,
            session_kid=os.getenv("KISANSATHI_SESSION_KID", "primary"),
            session_ttl_seconds=max(60, min(86_400, int(os.getenv("KISANSATHI_SESSION_TTL_SECONDS", "3600")))),
            csrf_ttl_seconds=max(60, min(86_400, int(os.getenv("KISANSATHI_CSRF_TTL_SECONDS", "3600")))),
            provider_configured=provider_configured,
            provider_error=provider_error,
            event_store_path=Path(os.getenv("KISANSATHI_HARNESS_EVENT_STORE_PATH", "/app/data/harness/events.jsonl")),
        )


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1, max_length=100_000)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: list[Message] = Field(min_length=1, max_length=64)
    turn_id: str | None = Field(default=None, min_length=1, max_length=128)
    workflow: str = Field(default="farm_context", min_length=1, max_length=128)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)


class ApprovalRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool
    payload_hash: str = Field(min_length=1, max_length=128)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)


def _session_manager(settings: HarnessSettings) -> SessionManager:
    return SessionManager(
        secret=settings.session_secret,
        kid=settings.session_kid,
        ttl_seconds=settings.session_ttl_seconds,
    )


def _build_orchestrator(settings: HarnessSettings, sessions: SessionManager) -> tuple[Orchestrator, str | None]:
    # Development remains deterministic and offline. Production never silently
    # falls back to a fake provider or accepts an unconfigured LLM.
    if not settings.provider_configured:
        if settings.environment == "production":
            return Orchestrator(provider=FakeProvider(configured=False), sessions=sessions, event_store=EventStore(storage_path=settings.event_store_path)), settings.provider_error or "provider is unavailable"
        return Orchestrator(provider=FakeProvider(), sessions=sessions, event_store=EventStore(storage_path=settings.event_store_path)), None
    try:
        runtime = ProviderRuntime.from_config(ProviderConfig.from_env())
    except Exception as exc:  # readiness exposes only a stable degraded code
        return Orchestrator(provider=FakeProvider(configured=False), sessions=sessions, event_store=EventStore(storage_path=settings.event_store_path)), str(exc)
    return Orchestrator.from_runtime(runtime, sessions=sessions, event_store=EventStore(storage_path=settings.event_store_path)), None


def _settings(request: Request) -> HarnessSettings:
    return request.app.state.settings


def _orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def _authenticate(request: Request, *, method: str, expected_session_id: str | None = None) -> HarnessSession:
    settings = _settings(request)
    manager: SessionManager = request.app.state.session_manager
    try:
        return authenticate_request(
            manager,
            cookies=request.cookies,
            headers=request.headers,
            method=method,
            expected_session_id=expected_session_id,
            csrf=CsrfTokenCodec(settings.csrf_secret, ttl_seconds=settings.csrf_ttl_seconds),
        )
    except HarnessAuthError as exc:
        status = 403 if exc.code == "session_forbidden" else 401
        raise HTTPException(status_code=status, detail=exc.code) from exc


def _owned_session(request: Request, session_id: str = ApiPath(...)) -> HarnessSession:
    authenticated = _authenticate(request, method=request.method, expected_session_id=session_id)
    try:
        return _orchestrator(request).require_session(authenticated.actor, session_id)
    except OrchestratorError as exc:
        raise HTTPException(status_code=403, detail=exc.code) from exc


def _ndjson(events: list[EventEnvelope] | tuple[EventEnvelope, ...]) -> AsyncIterator[str]:
    async def body() -> AsyncIterator[str]:
        for event in events:
            yield event.ndjson()

    return body()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app(settings: HarnessSettings | None = None) -> FastAPI:
    configured = settings or HarnessSettings.from_env()
    session_manager = _session_manager(configured)
    orchestrator, provider_error = _build_orchestrator(configured, session_manager)
    app = FastAPI(title="Kisan Sathi Harness", version="1.0.0", lifespan=lifespan)
    app.state.settings = configured
    app.state.provider_error = provider_error
    app.state.orchestrator = orchestrator
    app.state.session_manager = session_manager

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, Any]:
        return {"status": "ok", "service": "kisansathi-harness"}

    @app.get("/readyz", tags=["health"])
    async def readyz(response: Response) -> dict[str, Any]:
        ready = configured.environment != "production" or (
            configured.provider_configured and app.state.provider_error is None
        )
        if not ready:
            response.status_code = 503
        return {
            "status": "ready" if ready else "degraded",
            "service": "kisansathi-harness",
            "provider": "configured" if configured.provider_configured else "unavailable",
            "code": None if ready else "provider_unavailable",
        }

    @app.get("/capabilities", tags=["harness"])
    async def capabilities(request: Request) -> dict[str, Any]:
        session = _authenticate(request, method="GET")
        _orchestrator(request).require_session(session.actor, session.session_id)
        return {"service": "kisansathi-harness", "capabilities": _orchestrator(request).public_capabilities()}

    @app.post("/sessions", tags=["harness"])
    async def create_session(request: Request) -> dict[str, Any]:
        authenticated = _authenticate(request, method="POST")
        session, _, event = _orchestrator(request).start_session(authenticated.actor)
        return {"session_id": session.session_id, "actor": authenticated.actor.as_dict(), "event": event.as_dict()}

    @app.get("/sessions/{session_id}/events", tags=["harness"])
    async def replay_events(
        request: Request,
        session: HarnessSession = Depends(_owned_session),
        after: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        try:
            replay = _orchestrator(request).resume(session.actor, session.session_id, after)
        except OrchestratorError as exc:
            raise HTTPException(status_code=403, detail=exc.code) from exc
        if isinstance(replay, ResumeSnapshot):
            return StreamingResponse(_ndjson(()), status_code=409, media_type="text/event-stream", headers={"X-Resume-State": str(replay.as_dict())})
        return StreamingResponse(_ndjson(replay), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.post("/sessions/{session_id}/turns", tags=["harness"])
    async def send_turn(
        request: Request,
        payload: TurnRequest,
        session: HarnessSession = Depends(_owned_session),
    ) -> StreamingResponse:
        turn_id = payload.turn_id or f"turn-{uuid4().hex}"
        try:
            result = await _orchestrator(request).send_turn(
                session.actor,
                session.session_id,
                turn_id,
                tuple(message.model_dump() for message in payload.messages),
                workflow=payload.workflow,
                request_id=payload.request_id,
            )
        except OrchestratorError as exc:
            raise HTTPException(status_code=409 if exc.code == "turn_already_active" else 422, detail=exc.code) from exc
        return StreamingResponse(_ndjson(result.events), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.post("/sessions/{session_id}/approvals/{approval_id}", tags=["harness"])
    async def resolve_approval(
        request: Request,
        approval_id: str,
        payload: ApprovalRequestBody,
        session: HarnessSession = Depends(_owned_session),
    ) -> StreamingResponse:
        try:
            result = await _orchestrator(request).resolve_approval(
                session.actor,
                session.session_id,
                approval_id,
                accepted=payload.accepted,
                payload_hash=payload.payload_hash,
                request_id=payload.request_id,
            )
        except (OrchestratorError, ValueError, PermissionError) as exc:
            raise HTTPException(status_code=409, detail="approval_unavailable") from exc
        return StreamingResponse(_ndjson(result.events), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    @app.post("/sessions/{session_id}/turns/{turn_id}/cancel", tags=["harness"])
    async def cancel_turn(
        request: Request,
        turn_id: str,
        session: HarnessSession = Depends(_owned_session),
    ) -> dict[str, Any]:
        event = await _orchestrator(request).cancel(session.actor, session.session_id, turn_id)
        return event.as_dict()

    return app


app = create_app()
