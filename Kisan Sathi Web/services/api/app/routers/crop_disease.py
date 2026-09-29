from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import AuthenticatedSession, require_web_session
from app.services.crop_disease import get_crop_disease_service
from models.crop_disease.prototype import build_prototype_status

router = APIRouter(prefix="/v1/crop-disease", tags=["crop-disease"])


async def _image_body(request: Request, limit: int) -> bytes:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit:
        raise HTTPException(status_code=413, detail={"code": "image_too_large"})
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail={"code": "image_empty"})
    return content


@router.get("/models")
def models(request: Request, _: AuthenticatedSession = Depends(require_web_session)) -> dict:
    service = get_crop_disease_service(request)
    return {"models": [service.router.registry.public_entry(entry, service.router.downloaded_root) for entry in service.router.registry.entries]}


@router.get("/models/{model_id}")
def model(model_id: str, request: Request, _: AuthenticatedSession = Depends(require_web_session)) -> dict:
    service = get_crop_disease_service(request)
    try:
        entry = service.router.registry.get(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "model_not_found"}) from exc
    return service.router.registry.public_entry(entry, service.router.downloaded_root)


@router.get("/crops")
def crops(request: Request, _: AuthenticatedSession = Depends(require_web_session)) -> dict:
    service = get_crop_disease_service(request)
    return {"crops": sorted(service.router.registry.coverage(service.router.downloaded_root))}


@router.get("/coverage")
def coverage(request: Request, _: AuthenticatedSession = Depends(require_web_session)) -> dict:
    service = get_crop_disease_service(request)
    return {"coverage": service.router.registry.coverage(service.router.downloaded_root)}


@router.get("/prototype")
def prototype(request: Request, _: AuthenticatedSession = Depends(require_web_session)) -> dict:
    """Expose the non-production research profile used by the web prototype."""
    service = get_crop_disease_service(request)
    return build_prototype_status(service.router.registry, service.router.downloaded_root)


@router.post("/predict")
async def predict(
    request: Request,
    crop: str | None = Query(default=None),
    preferred_model: str | None = Query(default=None),
    top_k: int = Query(default=3, ge=1, le=10),
    mode: str = Query(default="single", pattern="^(single|ensemble)$"),
    _: AuthenticatedSession = Depends(require_web_session),
) -> dict:
    if not (request.headers.get("content-type") or "").casefold().startswith("image/"):
        raise HTTPException(status_code=415, detail={"code": "image_content_type_required"})
    service = get_crop_disease_service(request)
    try:
        result = service.predict(await _image_body(request, service.max_bytes), crop=crop, preferred_model=preferred_model, top_k=top_k, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_image", "message": str(exc)}) from exc
    return result.model_dump(mode="json")
