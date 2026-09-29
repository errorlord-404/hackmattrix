"""Server-side adapter for the optional crop.health provider.

Only crop-image bytes cross this provider boundary. Farmer identity, location,
and sensor readings remain in the KisanSathi assessment record.
"""

from __future__ import annotations

import base64
import asyncio
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path
from typing import Any

from app.core.config import settings


def configured() -> bool:
    return bool(settings.KINDWISE_CROP_HEALTH_API_KEY and settings.KINDWISE_CROP_HEALTH_BASE_URL)


def _candidate(item: dict[str, Any]) -> dict[str, Any]:
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    name = item.get("name") or item.get("common_name") or details.get("common_name") or details.get("name")
    return {"label": str(name or "unlabelled candidate"), "score": item.get("probability") or item.get("confidence"), "details": details}


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> tuple[int, bytes]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 -- operator-configured HTTPS provider endpoint
        return response.status, response.read()


async def assess_image(image_path: Path, confirmed_crop: str | None = None) -> dict[str, Any]:
    if not configured():
        return {"status": "provider_unavailable", "provider": "kindwise_crop_health", "error": "crop.health is not configured on this server.", "limitations": ["No hosted crop-health API key and base URL are configured."]}
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    # crop.health accepts the image list in its JSON body. Keep the
    # farmer-confirmed crop in KisanSathi's evidence record instead of sending
    # unsupported fields to the provider.
    payload: dict[str, Any] = {"images": [image_b64]}
    url = f"{settings.KINDWISE_CROP_HEALTH_BASE_URL.rstrip('/')}{settings.KINDWISE_CROP_HEALTH_IDENTIFICATION_PATH}"
    started = time.monotonic()
    try:
        status_code, raw_body = await asyncio.to_thread(
            _post_json, url, {"Api-Key": settings.KINDWISE_CROP_HEALTH_API_KEY}, payload,
            settings.KINDWISE_CROP_HEALTH_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return {"status": "provider_unavailable", "provider": "kindwise_crop_health", "error": "crop.health timed out.", "retryable": True}
    except HTTPError as exc:
        return {"status": "provider_unavailable", "provider": "kindwise_crop_health", "error": f"crop.health returned HTTP {exc.code}.", "retryable": exc.code >= 500}
    except (URLError, OSError) as exc:
        return {"status": "provider_unavailable", "provider": "kindwise_crop_health", "error": f"crop.health request failed: {exc.__class__.__name__}", "retryable": True}
    if status_code >= 400:
        return {"status": "provider_unavailable", "provider": "kindwise_crop_health", "error": f"crop.health returned HTTP {status_code}.", "retryable": status_code >= 500}
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "provider_unavailable", "provider": "kindwise_crop_health", "error": "crop.health returned an invalid response.", "retryable": False}
    raw = body.get("result") if isinstance(body, dict) and isinstance(body.get("result"), dict) else body
    disease = raw.get("disease") if isinstance(raw, dict) and isinstance(raw.get("disease"), dict) else {}
    # crop.health returns disease candidates below result.disease.suggestions.
    # Retain the legacy top-level fallback for compatible provider deployments.
    suggestions = disease.get("suggestions", []) if disease else raw.get("suggestions", []) if isinstance(raw, dict) else []
    candidates = [_candidate(item) for item in suggestions if isinstance(item, dict)][:5]
    if not candidates:
        return {"status": "inconclusive", "provider": "kindwise_crop_health", "crop": confirmed_crop, "disease_candidates": [], "limitations": ["The visual provider returned no usable crop-health candidates."], "provider_latency_ms": round((time.monotonic() - started) * 1000)}
    top = candidates[0]
    return {"status": "completed", "provider": "kindwise_crop_health", "crop": confirmed_crop, "label": top["label"], "confidence": top.get("score"), "disease_candidates": candidates, "provider_latency_ms": round((time.monotonic() - started) * 1000), "limitations": ["Visual provider candidates are screening evidence, not a confirmed diagnosis."]}
