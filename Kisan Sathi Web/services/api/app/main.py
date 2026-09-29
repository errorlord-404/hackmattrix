from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator, Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from .adapters.base import LLMAdapter, LLMAdapterError
from .adapters.openai_compatible import OpenAICompatibleAdapter
from .auth.dependencies import AuthenticatedSession, require_web_session, validate_session_id
from .contracts.models import ChatRequest, StreamEvent, ToolsResponse
from .registry.loader import RegistryError, ToolRegistry
from .settings import ServiceSettings, default_model_catalog_path, default_tool_contract_path
from .core.config import settings as api_settings
from .core.database import init_db
from .routers.domain import router as domain_router
from .routers.auth import router as auth_router
from .routers.reference import router as reference_router
from .routers.vision import router as vision_router
from .routers.media import router as media_router
from .routers.crop_disease import router as crop_disease_router


logger = logging.getLogger("kisansathi.api")


def _event(
    *,
    session_id: str,
    turn_id: str,
    sequence: int,
    kind: str,
    payload: dict[str, Any],
) -> str:
    event = StreamEvent(
        session_id=session_id,
        turn_id=turn_id,
        sequence=sequence,
        kind=kind,  # type: ignore[arg-type]
        payload=payload,
        delivery={"cursor": str(sequence), "replay": False, "duplicate": False},
    )
    return event.model_dump_json() + "\n"


def _safe_messages(request: ChatRequest, max_input_bytes: int) -> list[Mapping[str, str]]:
    messages = [{"role": message.role, "content": message.content} for message in request.messages]
    size = sum(len(item["content"].encode("utf-8")) for item in messages)
    if size > max_input_bytes:
        raise HTTPException(status_code=413, detail="Chat input exceeds the configured bound.")
    return messages


def create_app(
    settings: ServiceSettings | None = None,
    *,
    adapter: LLMAdapter | None = None,
    registry: ToolRegistry | None = None,
) -> FastAPI:
    service_settings = settings or ServiceSettings.from_env()
    if service_settings.environment == "production" and not service_settings.production_auth_configured and not service_settings.bearer_token:
        raise RuntimeError("Production startup requires OIDC discovery, audience, client identity, redirect URI, session/CSRF secrets, and internal context secret.")
    if registry is None:
        contract_path = service_settings.tool_contract_path or default_tool_contract_path()
        try:
            registry = ToolRegistry.from_json(
                contract_path, max_tools=service_settings.max_tools  # type: ignore[arg-type]
            )
        except RegistryError:
            # The app still starts so health diagnostics can report degraded
            # readiness without revealing a filesystem path.
            registry = ToolRegistry([])
            registry_error = True
        else:
            registry_error = False
    else:
        registry_error = False
    llm = adapter or OpenAICompatibleAdapter(
        base_url=service_settings.llm_base_url,
        api_key=service_settings.llm_api_key,
        model=service_settings.llm_model,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        reference_client = None
        app.state.reference_db_available = False
        app.state.reference_db_error = None
        if api_settings.reference_db_enabled:
            try:
                reference_client = await init_db()
                app.state.reference_db_available = True
            except Exception as exc:  # optional reference data is degraded, not a startup failure
                app.state.reference_db_error = str(exc)
        try:
            yield
        finally:
            if reference_client is not None:
                reference_client.close()

    app = FastAPI(title="Kisan Sathi API", version="1.0.0", lifespan=lifespan)
    app.state.settings = service_settings
    app.state.adapter = llm
    app.state.registry = registry
    app.state.registry_error = registry_error
    app.state.model_catalog_path = service_settings.model_catalog_path or default_model_catalog_path()

    @app.middleware("http")
    async def reject_legacy_farmer_selector(request: Request, call_next):
        forbidden_query_keys = {"farmer_id", "tenant_id", "farmer", "tenant"}
        if request.headers.get("X-Farmer-ID") is not None or any(key.casefold() in forbidden_query_keys for key in request.query_params):
            return Response(
                content='{"detail":{"code":"legacy_identity_selector_rejected","message":"Farmer identity is server-scoped and cannot be selected by a request header or query parameter.","retryable":false}}',
                status_code=400,
                media_type="application/json",
            )
        return await call_next(request)

    app.include_router(domain_router)
    app.include_router(reference_router)
    app.include_router(vision_router)
    app.include_router(media_router)
    app.include_router(crop_disease_router)
    app.include_router(auth_router)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "kisansathi-api",
            "provider": "configured" if llm.configured else "unavailable",
        }

    @app.get("/health", tags=["health"])
    async def health(request: Request) -> dict[str, Any]:
        from app.services.crop_disease import get_crop_disease_service
        from models.crop_disease.prototype import build_prototype_status

        try:
            crop_service = get_crop_disease_service(request)
            crop_profile = build_prototype_status(crop_service.router.registry, crop_service.router.downloaded_root)
            crop_models = crop_profile["status"]
        except Exception:
            crop_models = "unavailable"
        return {
            "status": "ok" if getattr(app.state, "reference_db_available", False) else "degraded",
            "service": "kisansathi-backend",
            "farm_state": "available",
            "reference_database": "available" if getattr(app.state, "reference_db_available", False) else "unavailable",
            "crop_models": crop_models,
        }

    @app.get("/readyz", tags=["health"])
    async def readyz(response: Response) -> dict[str, Any]:
        ready = bool(llm.configured and not app.state.registry_error)
        if not ready:
            response.status_code = 503
        return {
            "status": "ready" if ready else "degraded",
            "service": "kisansathi-api",
            "provider": "configured" if llm.configured else "unavailable",
            "tools": "loaded" if not app.state.registry_error else "unavailable",
        }

    @app.get("/tools", response_model=ToolsResponse, tags=["tools"])
    async def tools(_: AuthenticatedSession = Depends(require_web_session)) -> ToolsResponse:
        if app.state.registry_error:
            raise HTTPException(status_code=503, detail="Tool registry is unavailable.")
        items = app.state.registry.all()
        return ToolsResponse(
            schema_version=app.state.registry.schema_version,
            count=len(items),
            tools=items,
        )

    @app.post("/chat/stream", tags=["chat"])
    async def chat_stream(
        chat: ChatRequest,
        request: Request,
        authenticated: AuthenticatedSession = Depends(require_web_session),
    ) -> StreamingResponse:
        session_id = validate_session_id(chat.session_id, authenticated.session_id)
        turn_id = validate_session_id(chat.turn_id, f"turn-{uuid4().hex}")
        messages = _safe_messages(chat, service_settings.max_input_bytes)
        selected_tools = app.state.registry.select(
            chat.tool_names, max_tools=service_settings.max_tools
        )

        async def body() -> AsyncIterator[str]:
            sequence = 0

            def next_event(kind: str, payload: dict[str, Any]) -> str:
                nonlocal sequence
                sequence += 1
                return _event(
                    session_id=session_id,
                    turn_id=turn_id,
                    sequence=sequence,
                    kind=kind,
                    payload=payload,
                )

            try:
                if await request.is_disconnected():
                    return
                yield next_event(
                    "ready",
                    {"status": "ready", "provider": llm.provider_name},
                )
                if not llm.configured:
                    unavailable_result = {
                        "status": "degraded",
                        "code": "provider_unavailable",
                        "summary": "The configured language provider is unavailable.",
                    }
                    yield next_event(
                        "unavailable",
                        {
                            "status": "degraded",
                            "code": "provider_unavailable",
                            "message": "The configured language provider is unavailable.",
                            "result": unavailable_result,
                        },
                    )
                    yield next_event(
                        "turnCompleted",
                        {"status": "degraded", "provider": "unavailable"},
                    )
                    return

                completed_text: list[str] = []
                async for chunk in llm.stream_chat(messages, selected_tools):
                    if await request.is_disconnected():
                        return
                    if chunk.text:
                        completed_text.append(chunk.text)
                        yield next_event("agentMessageDelta", {"text": chunk.text})
                if await request.is_disconnected():
                    return
                yield next_event(
                    "agentMessageCompleted",
                    {"text": "".join(completed_text)},
                )
                yield next_event(
                    "turnCompleted",
                    {"status": "ok", "provider": llm.provider_name},
                )
            except asyncio.CancelledError:
                # Cancellation propagates to StreamingResponse and upstream
                # adapter cleanup; no half-success event is emitted.
                raise
            except LLMAdapterError as exc:
                logger.warning(
                    "provider stream failed code=%s retryable=%s",
                    exc.code,
                    exc.retryable,
                )
                yield next_event(
                    "diagnostic",
                    {
                        "status": "degraded",
                        "code": exc.code,
                        "retryable": exc.retryable,
                    },
                )
                yield next_event(
                    "turnCompleted",
                    {"status": "degraded", "provider": llm.provider_name},
                )
            finally:
                await llm.aclose()

        return StreamingResponse(body(), media_type="application/x-ndjson")

    return app


app = create_app()
