from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedSession
from app.core.config import settings as api_settings
from app.farm_state.store import FarmStateStore, get_idempotent_response, save_idempotent_response, validate_idempotency_key


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 10 * 1024 * 1024

_IMAGE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
_AUDIO_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "audio/wav": (b"RIFF",),
    "audio/x-wav": (b"RIFF",),
    "audio/webm": (b"\x1a\x45\xdf\xa3",),
    "audio/ogg": (b"OggS",),
    "audio/mpeg": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
}


@dataclass(frozen=True, slots=True)
class MediaResult:
    status: str
    request_id: str
    upload_id: str
    content_sha256: str
    language: str | None = None
    field_id: str | None = None
    crop: str | None = None
    code: str | None = None
    message: str = ""
    transcript: str | None = None
    diagnosis: None = None

    def as_dict(self) -> dict[str, Any]:
        result = {key: value for key, value in {
            "status": self.status,
            "request_id": self.request_id,
            "upload_id": self.upload_id,
            "content_sha256": self.content_sha256,
            "language": self.language,
            "field_id": self.field_id,
            "crop": self.crop,
            "code": self.code,
            "message": self.message,
            "transcript": self.transcript,
            "diagnosis": self.diagnosis,
        }.items() if value is not None}
        result.setdefault("transcript", self.transcript)
        result.setdefault("diagnosis", self.diagnosis)
        return result


def _bad(code: str, message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "retryable": False})


def _validate_type(content_type: str | None, content: bytes, signatures: dict[str, tuple[bytes, ...]]) -> str:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    allowed = signatures.get(normalized)
    if not allowed or not any(content.startswith(signature) for signature in allowed):
        raise _bad("media_type_mismatch", "The content type does not match an allowed file signature.")
    if normalized == "image/webp" and content[8:12] != b"WEBP":
        raise _bad("media_type_mismatch", "The WebP signature is invalid.")
    if normalized in {"audio/wav", "audio/x-wav"} and content[8:12] != b"WAVE":
        raise _bad("media_type_mismatch", "The WAV signature is invalid.")
    return normalized


def _store_private(actor: AuthenticatedSession, kind: str, content: bytes, content_type: str) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    upload_id = f"{kind}-{uuid4().hex}"
    store = FarmStateStore(tenant_id=actor.actor.tenant_id, farmer_id=actor.actor.farmer_id)
    try:
        path = store.upload_dir / f"{upload_id}.bin"
        path.write_bytes(content)
        metadata = {"upload_id": upload_id, "kind": kind, "content_type": content_type, "sha256": digest}
        path.with_suffix(".json").write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
    finally:
        store.close()
    return upload_id, digest


def _assert_field_owned(actor: AuthenticatedSession, field_id: str) -> None:
    store = FarmStateStore(tenant_id=actor.actor.tenant_id, farmer_id=actor.actor.farmer_id)
    try:
        if store.one("SELECT id FROM fields WHERE id = ? AND active = 1", (field_id,)) is None:
            raise _bad("field_not_found", "The selected field is not owned by the authenticated farmer.", 404)
    finally:
        store.close()


def _cached(store: FarmStateStore, key: str | None, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not key:
        return None
    try:
        validate_idempotency_key(key)
        return get_idempotent_response(store, key, payload)
    except ValueError as exc:
        raise _bad("idempotency_key_conflict", str(exc), 409) from exc


def _save(actor: AuthenticatedSession, key: str | None, payload: dict[str, Any], result: dict[str, Any]) -> None:
    if not key:
        return
    store = FarmStateStore(tenant_id=actor.actor.tenant_id, farmer_id=actor.actor.farmer_id)
    try:
        save_idempotent_response(store, key, payload, result)
    finally:
        store.close()


def process_image(actor: AuthenticatedSession, content: bytes, content_type: str | None, *, field_id: str | None, crop: str | None, idempotency_key: str | None, request_id: str) -> dict[str, Any]:
    if not field_id or not crop:
        raise _bad("field_and_crop_required", "A confirmed owned field and crop are required before image analysis.")
    _assert_field_owned(actor, field_id)
    if len(content) > MAX_IMAGE_BYTES:
        raise _bad("image_too_large", "Image exceeds the 10 MB upload limit.", 413)
    normalized_type = _validate_type(content_type, content, _IMAGE_SIGNATURES)
    digest = hashlib.sha256(content).hexdigest()
    payload = {"kind": "image", "field_id": field_id, "crop": crop, "content_type": normalized_type, "sha256": digest}
    store = FarmStateStore(tenant_id=actor.actor.tenant_id, farmer_id=actor.actor.farmer_id)
    try:
        cached = _cached(store, idempotency_key, payload)
    finally:
        store.close()
    if cached is not None:
        return cached
    upload_id, _ = _store_private(actor, "image", content, normalized_type)
    result = MediaResult("inconclusive", request_id, upload_id, digest, field_id=field_id, crop=crop, code="cv_release_unavailable", message="Image received, but no approved diagnostic model is enabled. A qualified agronomist should review it.").as_dict()
    _save(actor, idempotency_key, payload, result)
    return result


def process_voice(actor: AuthenticatedSession, content: bytes, content_type: str | None, *, language: str, idempotency_key: str | None, request_id: str) -> dict[str, Any]:
    if len(content) > MAX_AUDIO_BYTES:
        raise _bad("audio_too_large", "Audio exceeds the 10 MB upload limit.", 413)
    normalized_type = _validate_type(content_type, content, _AUDIO_SIGNATURES)
    safe_language = language.strip()[:32] or "en-IN"
    digest = hashlib.sha256(content).hexdigest()
    payload = {"kind": "voice", "language": safe_language, "content_type": normalized_type, "sha256": digest}
    store = FarmStateStore(tenant_id=actor.actor.tenant_id, farmer_id=actor.actor.farmer_id)
    try:
        cached = _cached(store, idempotency_key, payload)
    finally:
        store.close()
    if cached is not None:
        return cached
    upload_id, _ = _store_private(actor, "voice", content, normalized_type)
    result = MediaResult("unavailable", request_id, upload_id, digest, language=safe_language, code="voice_provider_unavailable", message="Voice processing is unavailable because no approved speech provider is configured.").as_dict()
    _save(actor, idempotency_key, payload, result)
    return result
