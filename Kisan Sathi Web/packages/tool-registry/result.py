"""The bounded result envelope shared by every registered tool."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


DEFAULT_MAX_RESPONSE_BYTES = 32 * 1024
_SENSITIVE_KEY = re.compile(
    r"(?:authorization|api[-_]?key|access[-_]?token|refresh[-_]?token|client[-_]?secret|"
    r"password|credential|secret|cookie|private[-_]?key|session[-_]?token)",
    re.IGNORECASE,
)


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def redact_secrets(value: Any) -> Any:
    """Recursively remove values under secret-bearing keys before bounding."""

    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _SENSITIVE_KEY.search(key_text):
                safe[key_text] = "[REDACTED]"
            else:
                safe[key_text] = redact_secrets(item)
        return safe
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value


def _bounded_fallback(value: Any, max_bytes: int) -> Any:
    marker = {"truncated": True}
    if isinstance(value, list):
        items: list[Any] = []
        for item in value:
            candidate = {"items": items + [item], "truncated": True, "total_items": len(value)}
            if _json_size(candidate) > max_bytes:
                break
            items.append(item)
        candidate = {"items": items, "truncated": True, "total_items": len(value)}
        if _json_size(candidate) <= max_bytes:
            return candidate
    elif isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in value.items():
            candidate = dict(compact)
            candidate[str(key)] = item
            candidate["truncated"] = True
            if _json_size(candidate) > max_bytes:
                break
            compact[str(key)] = item
        compact["truncated"] = True
        if _json_size(compact) <= max_bytes:
            return compact

    # Keep the envelope valid even when a single scalar is larger than the bound.
    text = str(value)
    available = max(0, max_bytes - _json_size(marker) - 16)
    while available and _json_size({"value": text[:available], "truncated": True}) > max_bytes:
        available -= max(1, min(128, available))
    return {"value": text[:available], "truncated": True}


def bound_data(data: Any, max_bytes: int) -> tuple[Any, bool]:
    """Return secret-safe data and whether its JSON representation was bounded."""

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    safe = redact_secrets(data)
    if _json_size(safe) <= max_bytes:
        return safe, False
    return _bounded_fallback(safe, max_bytes), True


def _resource_type(path: str) -> str:
    parts = [part for part in path.strip("/").split("/") if part]
    resources = {
        "fields": "field",
        "crop-cycles": "crop_cycle",
        "soil-tests": "soil_test",
        "sensor-readings": "sensor_reading",
        "irrigation-events": "irrigation_event",
        "tasks": "field_task",
        "reminders": "reminder",
        "alerts": "alert",
        "reports": "report",
        "profile": "profile",
        "diagnoses": "diagnosis",
        "advisor": "advisor_session",
    }
    for token in reversed(parts):
        if token in resources:
            return resources[token]
    token = parts[1] if len(parts) > 1 and parts[0] == "v1" else parts[0] if parts else "unknown"
    return token.rstrip("s")


def _refresh_hints(resource_type: str) -> list[str]:
    return {
        "field": ["dashboard", "fields", "map"],
        "crop_cycle": ["fields", "timeline", "dashboard"],
        "soil_test": ["soil", "dashboard"],
        "sensor_reading": ["soil", "irrigation", "alerts", "dashboard"],
        "irrigation_event": ["irrigation", "timeline", "dashboard"],
        "field_task": ["tasks", "fields", "dashboard"],
        "reminder": ["reminders", "dashboard"],
        "alert": ["alerts", "dashboard"],
        "report": ["reports"],
        "profile": ["settings", "dashboard"],
        "diagnosis": ["advisor", "diagnosis"],
        "advisor_session": ["advisor"],
    }.get(resource_type, [resource_type])


def write_action(path: str, method: str, data: Any, *, source: str = "kisansathi_backend") -> dict[str, Any]:
    """Describe an authoritative persistent response for UI refresh/audit."""

    affected_ids: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if (key == "id" or key.endswith("_id")) and isinstance(value, (str, int)):
                affected_ids[key] = str(value)
    resource_type = _resource_type(path)
    return {
        "method": method.upper(),
        "path": path,
        "resource_type": resource_type,
        "affected_ids": affected_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "warnings": [],
        "refresh": _refresh_hints(resource_type),
    }


def tool_result(
    *,
    status: str,
    summary: str,
    data: Any = None,
    source: str = "kisansathi_backend",
    request_id: str | None = None,
    warnings: list[str] | None = None,
    freshness: Any = None,
    action: dict[str, Any] | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    """Create the schema-complete, bounded, provider-neutral result envelope."""

    if not summary or len(summary) > 2000:
        raise ValueError("summary must contain 1-2000 characters")
    max_response_bytes = max(1, min(int(max_response_bytes), 1024 * 1024))
    bounded, truncated = bound_data(data, max_response_bytes)
    return {
        "status": status,
        "summary": summary,
        "data": bounded,
        "source": source,
        "warnings": [str(item)[:500] for item in (warnings or [])],
        "request_id": request_id or f"req-{uuid4().hex}",
        "freshness": freshness,
        "bounds": {"max_bytes": max_response_bytes, "truncated": truncated},
        "action": action,
    }


def tool_error(
    *,
    summary: str,
    code: str,
    retryable: bool,
    request_id: str | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    return tool_result(
        status="error",
        summary=summary,
        data={"code": code, "retryable": bool(retryable)},
        source="kisansathi_backend",
        request_id=request_id,
        max_response_bytes=max_response_bytes,
    )


def tool_degraded(
    *,
    summary: str,
    data: Any = None,
    warning: str,
    request_id: str | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    return tool_result(
        status="degraded",
        summary=summary,
        data=data,
        source="kisansathi_backend",
        request_id=request_id,
        warnings=[warning],
        max_response_bytes=max_response_bytes,
    )
