from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from app.auth.dependencies import AuthenticatedSession, require_web_session
from app.services.media import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES, process_image, process_voice


router = APIRouter(prefix="/v1/media", tags=["media"])


async def _bounded_body(request: Request, limit: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > limit:
        raise HTTPException(status_code=413, detail={"code": "media_too_large", "message": "The media upload exceeds the configured bound.", "retryable": False})
    body = await request.body()
    if len(body) > limit:
        raise HTTPException(status_code=413, detail={"code": "media_too_large", "message": "The media upload exceeds the configured bound.", "retryable": False})
    if not body:
        raise HTTPException(status_code=400, detail={"code": "media_empty", "message": "Media content is required.", "retryable": False})
    return body


@router.get("/capabilities")
def media_capabilities(_: AuthenticatedSession = Depends(require_web_session)) -> dict[str, object]:
    return {"voice": {"status": "unavailable", "max_bytes": MAX_AUDIO_BYTES}, "image": {"status": "inconclusive", "max_bytes": MAX_IMAGE_BYTES, "diagnostic_model": "none_approved"}}


@router.post("/image")
async def image_upload(
    request: Request,
    authenticated: AuthenticatedSession = Depends(require_web_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    field_id: str | None = Header(default=None, alias="X-Field-ID"),
    crop: str | None = Header(default=None, alias="X-Crop-Name"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, object]:
    body = await _bounded_body(request, MAX_IMAGE_BYTES)
    return process_image(authenticated, body, request.headers.get("content-type"), field_id=field_id, crop=crop, idempotency_key=idempotency_key, request_id=request_id or f"request-{uuid4().hex}")


@router.post("/voice")
async def voice_upload(
    request: Request,
    authenticated: AuthenticatedSession = Depends(require_web_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    language: str = Header(default="en-IN", alias="Accept-Language"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict[str, object]:
    body = await _bounded_body(request, MAX_AUDIO_BYTES)
    return process_voice(authenticated, body, request.headers.get("content-type"), language=language, idempotency_key=idempotency_key, request_id=request_id or f"request-{uuid4().hex}")
