"""Export deterministic API and tool metadata without importing the parent app."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


OPENAPI_PATHS = {
    "/crops": ["get", "post"], "/crops/{crop_id}": ["delete", "get", "put"],
    "/diseases": ["get", "post"], "/diseases/{disease_id}": ["delete", "get", "put"],
    "/farmers": ["get", "post"], "/farmers/{farmer_id}": ["delete", "get", "put"],
    "/fertilizer": ["get", "post"], "/fertilizer/recommend": ["post"],
    "/fertilizer/{fertilizer_id}": ["delete", "get", "put"], "/gov-schemes": ["get", "post"],
    "/gov-schemes/by-state/{state}": ["get"], "/gov-schemes/check-eligibility": ["post"],
    "/gov-schemes/{gov_scheme_id}": ["delete", "get", "put"], "/health": ["get"],
    "/internal/universal-data/runs": ["get"], "/internal/universal-data/sync": ["post"],
    "/machinery-rentals": ["get", "post"], "/machinery-rentals/nearby": ["get"],
    "/machinery-rentals/{rental_id}": ["delete", "get", "put"], "/market-prices": ["get", "post"],
    "/market-prices/by-crop/{crop_name}": ["get"], "/market-prices/compare/{crop_name}": ["get"],
    "/market-prices/history": ["get"], "/market-prices/summary": ["get"],
    "/market-prices/trend": ["get"], "/market-prices/{market_price_id}": ["delete", "get", "put"],
    "/marketplace/compare-quotes": ["post"], "/marketplace/listings": ["get"],
    "/marketplace/nearby": ["get"], "/marketplace/status": ["get"],
    "/msp": ["get", "post"], "/msp/by-crop/{crop_name}": ["get"], "/msp/compare-market": ["get"],
    "/msp/{msp_id}": ["delete", "get", "put"], "/seeds": ["get", "post"],
    "/seeds/recommend": ["post"], "/seeds/{seed_id}": ["delete", "get", "put"],
    "/v1/advisor/sessions": ["post"], "/v1/advisor/sessions/{session_id}/messages": ["post"],
    "/v1/advisor/sessions/{session_id}/stream": ["get"], "/v1/alerts": ["get"],
    "/v1/alerts/{alert_id}": ["patch"], "/v1/audit": ["get"],
    "/v1/crop-cycles/{cycle_id}/stage": ["patch"], "/v1/dashboard": ["get"],
    "/v1/demo/load": ["post"], "/v1/device-ingestion/devices": ["get"],
    "/v1/device-ingestion/observations": ["post"], "/v1/diagnoses": ["post"],
    "/v1/diagnoses/{diagnosis_id}": ["get"], "/v1/diagnoses/{diagnosis_id}/feedback": ["post"],
    "/v1/diagnostics": ["get"], "/v1/export": ["get"], "/v1/fields": ["get", "post"],
    "/v1/fields/map": ["get"], "/v1/fields/{field_id}": ["delete", "get", "patch"],
    "/v1/fields/{field_id}/action-proposals": ["get"], "/v1/fields/{field_id}/crop-cycles": ["post"],
    "/v1/fields/{field_id}/crop-options": ["get"], "/v1/fields/{field_id}/irrigation-plan": ["get"],
    "/v1/fields/{field_id}/observations/history": ["get"], "/v1/fields/{field_id}/observations/latest": ["get"],
    "/v1/fields/{field_id}/soil-health": ["get"], "/v1/fields/{field_id}/soil-tests": ["post"],
    "/v1/fields/{field_id}/timeline": ["get"], "/v1/irrigation-events": ["get", "post"],
    "/v1/ledger/entries": ["get", "post"], "/v1/ledger/entries/{entry_id}": ["patch"],
    "/v1/ledger/summary": ["get"], "/v1/profile": ["get", "put"], "/v1/reminders": ["get", "post"],
    "/v1/reports": ["get", "post"], "/v1/reports/{report_id}": ["get"],
    "/v1/sarvam/runtime-config": ["get", "put"], "/v1/sensor-readings": ["post"],
    "/v1/storage-status": ["get"], "/v1/tasks": ["get", "post"], "/v1/tasks/{task_id}": ["patch"],
    "/v1/translate": ["post"], "/v1/voice/synthesize": ["post"], "/v1/voice/transcribe": ["post"],
    "/v1/voice/turns": ["post"], "/v1/weather": ["get"], "/v1/weather/alerts": ["get"],
}

FRONTEND_PATHS = [
    "/crops", "/gov-schemes", "/gov-schemes/by-state/{}", "/health", "/machinery-rentals", "/machinery-rentals/nearby",
    "/market-prices/compare/{}", "/market-prices/history", "/market-prices/summary", "/market-prices/trend", "/marketplace/listings",
    "/marketplace/nearby", "/marketplace/status", "/msp/compare-market", "/v1/advisor/sessions", "/v1/advisor/sessions/{}/messages",
    "/v1/alerts", "/v1/alerts/{}", "/v1/audit", "/v1/dashboard", "/v1/demo/load", "/v1/diagnoses", "/v1/diagnoses/{}",
    "/v1/diagnoses/{}/feedback", "/v1/diagnostics", "/v1/export", "/v1/fields", "/v1/fields/map", "/v1/fields/{}",
    "/v1/fields/{}/action-proposals", "/v1/fields/{}/crop-options", "/v1/fields/{}/irrigation-plan", "/v1/fields/{}/observations/history",
    "/v1/fields/{}/observations/latest", "/v1/fields/{}/soil-health", "/v1/fields/{}/timeline", "/v1/irrigation-events",
    "/v1/ledger/entries", "/v1/ledger/entries/{}", "/v1/ledger/summary", "/v1/profile", "/v1/reminders", "/v1/reports",
    "/v1/sarvam/runtime-config", "/v1/storage-status", "/v1/tasks", "/v1/tasks/{}", "/v1/translate", "/v1/voice/synthesize",
    "/v1/voice/transcribe", "/v1/voice/turns", "/v1/weather", "/v1/weather/alerts",
]

SOURCE_HASH_FILES = (
    "backend/app/main.py", "backend/app/routers/farm_state.py", "backend/app/routers/assistants.py",
    "src/api/farmStateApi.js", "src/api/referenceApi.js", "agent/src/kisansathi_agent/server.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frontend_paths(repo_root: Path) -> list[str]:
    literal_pattern = re.compile(r"[\"'`]((?:\$\{[^}]+\}|[^\"'`])*)[\"'`]")
    paths: set[str] = set()
    for relative in ("src/api/farmStateApi.js", "src/api/referenceApi.js"):
        for match in literal_pattern.finditer((repo_root / relative).read_text(encoding="utf-8")):
            raw = match.group(1)
            if not raw.startswith(("/v1", "/health", "/crops", "/market", "/msp", "/gov-", "/machinery-", "/marketplace")):
                continue
            raw = re.sub(r"\$\{queryString\(.*?\)\}", "", raw)
            raw = re.sub(r"\$\{[^}]+\}", "{}", raw).split("?")[0]
            raw = re.sub(r"\{[^}]+\}", "{}", raw)
            paths.add(raw.rstrip("/") or "/")
    return sorted(paths)


def _generic_schema(function: ast.AST) -> dict:
    if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return {"type": "object", "additionalProperties": False, "properties": {}}
    properties = {}
    for arg in function.args.args:
        if arg.arg == "self":
            continue
        properties[arg.arg] = {"type": "string"}
    return {"type": "object", "additionalProperties": False, "properties": properties}


def tool_inventory(repo_root: Path) -> list[dict]:
    server_path = repo_root / "agent/src/kisansathi_agent/server.py"
    tools_path = repo_root / "agent/src/kisansathi_agent/tools.py"
    server = ast.parse(server_path.read_text(encoding="utf-8"))
    tools = ast.parse(tools_path.read_text(encoding="utf-8"))
    methods = {node.name: node for node in ast.walk(tools) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    inventory = []
    for node in ast.walk(server):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "register"):
            continue
        name = node.args[0].value
        description = node.args[1].value
        callback = node.args[2].attr if isinstance(node.args[2], ast.Attribute) else name
        write = len(node.args) >= 4
        schema = _generic_schema(methods.get(callback))
        inventory.append({
            "name": name, "description": description, "access": "write" if write else "read",
            "annotations": {"readOnlyHint": not write, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
            "input_schema": schema,
            "capabilities": ["text"],
        })
    return sorted(inventory, key=lambda item: item["name"])


def build_baselines(repo_root: Path) -> tuple[dict, dict]:
    if len(OPENAPI_PATHS) != 84 or len(FRONTEND_PATHS) != 53:
        raise ValueError("canonical API path counts are inconsistent")
    if _frontend_paths(repo_root) != sorted(FRONTEND_PATHS):
        raise ValueError("frontend adapter path shapes drifted from the frozen inventory")
    inventory = tool_inventory(repo_root)
    counts = {"read": sum(item["access"] == "read" for item in inventory), "write": sum(item["access"] == "write" for item in inventory)}
    if len(inventory) != 78 or counts != {"read": 56, "write": 22}:
        raise ValueError(f"tool inventory drifted: {len(inventory)} tools, {counts}")
    source_hashes = {path: _sha256(repo_root / path) for path in SOURCE_HASH_FILES}
    return (
        {"schema_version": 1, "source_hashes": source_hashes, "counts": {"openapi_path_shapes": 84, "frontend_used_path_shapes": 53}, "paths": OPENAPI_PATHS, "frontend_paths": sorted(FRONTEND_PATHS)},
        {"schema_version": 1, "source_hashes": {"agent/src/kisansathi_agent/server.py": source_hashes["agent/src/kisansathi_agent/server.py"], "agent/src/kisansathi_agent/tools.py": _sha256(repo_root / "agent/src/kisansathi_agent/tools.py")}, "counts": counts, "tools": inventory},
    )


def check_baselines(repo_root: Path, output: Path) -> bool:
    expected_openapi, expected_tools = build_baselines(repo_root)
    try:
        return json.loads((output / "openapi-baseline.json").read_text(encoding="utf-8")) == expected_openapi and json.loads((output / "tool-registry-baseline.json").read_text(encoding="utf-8")) == expected_tools
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    openapi, tools = build_baselines(args.source_root.resolve())
    if args.check:
        ok = check_baselines(args.source_root.resolve(), args.output)
        print("baseline export: PASS" if ok else "baseline export: FAIL")
        return 0 if ok else 1
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "openapi-baseline.json").write_text(json.dumps(openapi, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "tool-registry-baseline.json").write_text(json.dumps(tools, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"exported {len(openapi['paths'])} API paths, {len(openapi['frontend_paths'])} frontend shapes, {len(tools['tools'])} tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
