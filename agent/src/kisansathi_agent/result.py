from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def bound_data(data: Any, max_bytes: int) -> Any:
    """Keep model-visible payloads bounded while preserving the useful prefix."""

    try:
        if len(json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")) <= max_bytes:
            return data
    except (TypeError, ValueError):
        return {"value": str(data), "truncated": True}

    if isinstance(data, list):
        items: list[Any] = []
        for item in data:
            candidate = items + [item]
            size = len(json.dumps(candidate, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
            if size > max_bytes * 0.85:
                break
            items.append(item)
        return {"items": items, "truncated": True, "total_items": len(data)}
    if isinstance(data, dict):
        compact: dict[str, Any] = {}
        for key, value in data.items():
            compact[str(key)] = value
            size = len(json.dumps(compact, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
            if size > max_bytes * 0.85:
                compact.pop(str(key), None)
                break
        compact["truncated"] = True
        return compact
    return {"value": str(data)[: max_bytes // 2], "truncated": True}


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
    max_response_bytes: int | None = None,
) -> dict[str, Any]:
    """Return the stable envelope consumed by the conversational agent."""

    result: dict[str, Any] = {
        "status": status,
        "summary": summary,
        "data": bound_data(data, max_response_bytes) if max_response_bytes else data,
        "source": source,
        "warnings": warnings or [],
    }
    if request_id:
        result["request_id"] = request_id
    if freshness is not None:
        result["freshness"] = freshness
    if action is not None:
        result["action"] = action
    return result


def write_action(path: str, method: str, data: Any) -> dict[str, Any]:
    """Describe a successful persistent write for UI refresh and audit rendering."""

    resource_type = _resource_type(path)
    affected_ids: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "id" or key.endswith("_id"):
                if isinstance(value, (str, int)):
                    affected_ids[key] = str(value)
    refresh = _refresh_hints(resource_type)
    return {
        "method": method,
        "path": path,
        "resource_type": resource_type,
        "affected_ids": affected_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "kisansathi_backend",
        "warnings": [],
        "refresh": refresh,
    }


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
    mapping = {
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
    }
    return mapping.get(resource_type, [resource_type])


def tool_error(
    *,
    summary: str,
    code: str,
    retryable: bool,
    request_id: str | None = None,
) -> dict[str, Any]:
    return tool_result(
        status="error",
        summary=summary,
        data={"code": code, "retryable": retryable},
        source="kisansathi_backend",
        request_id=request_id,
    )


def tool_degraded(
    *,
    summary: str,
    data: Any = None,
    warning: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    return tool_result(
        status="degraded",
        summary=summary,
        data=data,
        source="kisansathi_backend",
        request_id=request_id,
        warnings=[warning],
    )
