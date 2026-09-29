from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.dependencies import AuthenticatedSession, require_web_session
from app.services.model_catalog import HierarchicalModelCatalog, ModelCatalogError
from app.core.config import settings as api_settings
from models.crop_disease.router import CONTROLLED_WARNING
from app.services.vision_release import VisionReleaseUnavailable, load_approved_descriptor
from app.farm_state.store import FarmStateStore, get_idempotent_response, save_idempotent_response, validate_idempotency_key


router = APIRouter(prefix="/v1/vision", tags=["vision"])


class BrowserCandidate(BaseModel):
    upload_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    content_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    release_id: str = Field(min_length=1, max_length=160)
    preprocessing_version: str = Field(min_length=1, max_length=120)
    candidate: dict[str, Any] = Field(default_factory=dict)
    descriptor_signature: str | None = Field(default=None, min_length=64, max_length=128)
    descriptor_expires_at: str | None = Field(default=None, max_length=80)


@router.get("/capabilities")
def vision_capabilities(
    request: Request,
    _: AuthenticatedSession = Depends(require_web_session),
) -> dict:
    try:
        catalog = HierarchicalModelCatalog.from_path(request.app.state.model_catalog_path)
    except ModelCatalogError as exc:
        raise HTTPException(status_code=503, detail={"code": "model_catalog_unavailable", "message": str(exc)}) from exc
    return catalog.public_capabilities()


@router.get("/descriptor")
def vision_descriptor(
    request: Request,
    _: AuthenticatedSession = Depends(require_web_session),
) -> dict:
    """Return only a validated descriptor; no placeholder is browser-loadable."""
    try:
        return load_approved_descriptor(
            api_settings.runtime_cv_release_manifest_path,
            api_settings.runtime_cv_approval_record_path,
            api_settings.cv_descriptor_signing_secret,
        )
    except VisionReleaseUnavailable:
        return {"status": "unavailable", "activationAllowed": False, "reason": "approved_release_unavailable", "warnings": [CONTROLLED_WARNING]}


@router.post("/fallback")
async def vision_fallback(
    request: Request,
    _: AuthenticatedSession = Depends(require_web_session),
) -> dict:
    """Safe server fallback surface; it never returns a browser-only diagnosis."""
    from app.services.crop_disease import get_crop_disease_service

    service = get_crop_disease_service(request)
    content = await request.body()
    crop = request.headers.get("X-Crop-Name")
    try:
        result = service.predict(content, crop=crop)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_image", "message": str(exc)}) from exc
    return result.model_dump(mode="json")


@router.post("/finalize")
async def finalize_browser_candidate(
    payload: BrowserCandidate,
    request: Request,
    field_id: str | None = Header(default=None, alias="X-Field-ID"),
    crop: str | None = Header(default=None, alias="X-Crop-Name"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    authenticated: AuthenticatedSession = Depends(require_web_session),
) -> dict[str, Any]:
    """Revalidate a browser candidate and persist only a safe review state."""
    if not field_id or not crop:
        raise HTTPException(status_code=400, detail={"code": "field_and_crop_required", "message": "Owned field and confirmed crop are required."})
    if idempotency_key:
        try:
            validate_idempotency_key(idempotency_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_idempotency_key", "message": str(exc)}) from exc
    store = FarmStateStore(tenant_id=authenticated.actor.tenant_id, farmer_id=authenticated.actor.farmer_id)
    try:
        if store.one("SELECT id FROM fields WHERE id=? AND active=1", (field_id,)) is None:
            raise HTTPException(status_code=404, detail={"code": "field_not_found", "message": "The field is not owned by the authenticated farmer."})
        metadata_path = store.upload_dir / f"{payload.upload_id}.json"
        if not metadata_path.is_file():
            raise HTTPException(status_code=404, detail={"code": "upload_not_found", "message": "The upload is not owned by the authenticated farmer."})
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("sha256", "").casefold() != payload.content_sha256.casefold():
            raise HTTPException(status_code=409, detail={"code": "upload_checksum_mismatch", "message": "The browser candidate is not bound to the uploaded bytes."})
        request_payload = {"upload_id": payload.upload_id, "content_sha256": payload.content_sha256.casefold(), "release_id": payload.release_id, "preprocessing_version": payload.preprocessing_version, "descriptor_signature": payload.descriptor_signature, "descriptor_expires_at": payload.descriptor_expires_at, "candidate": payload.candidate, "field_id": field_id, "crop": crop}
        if idempotency_key:
            try:
                cached = get_idempotent_response(store, idempotency_key, request_payload)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
            if cached is not None:
                return cached
        try:
            descriptor = load_approved_descriptor(
                api_settings.runtime_cv_release_manifest_path,
                api_settings.runtime_cv_approval_record_path,
                api_settings.cv_descriptor_signing_secret,
            )
        except VisionReleaseUnavailable:
            descriptor = None
        if descriptor is not None:
            if payload.release_id != descriptor["releaseId"] or payload.preprocessing_version != descriptor["preprocessingVersion"]:
                raise HTTPException(status_code=409, detail={"code": "vision_descriptor_mismatch", "message": "The browser candidate is bound to a different approved release or preprocessing contract."})
            if payload.descriptor_signature != descriptor["signature"] or payload.descriptor_expires_at != descriptor["expiresAt"]:
                raise HTTPException(status_code=409, detail={"code": "vision_descriptor_untrusted", "message": "The browser descriptor signature or expiry could not be verified."})
        result = {
            "status": "needs_expert_review",
            "authoritative": False,
            "code": "cv_release_unavailable",
            "request_id": request.headers.get("X-Request-ID"),
            "upload_id": payload.upload_id,
            "content_sha256": payload.content_sha256.casefold(),
            "field_id": field_id,
            "crop": crop,
            "release_id": payload.release_id,
            "message": "The browser candidate was received but no approved CV release is enabled; no diagnosis was persisted.",
            "warnings": [CONTROLLED_WARNING],
        }
        if idempotency_key:
            save_idempotent_response(store, idempotency_key, request_payload, result)
        return result
    finally:
        store.close()
