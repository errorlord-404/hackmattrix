"""Canonical provider-neutral KisanSathi tool inventory.

The JSON contract under ``packages/contracts`` is the frozen parity artifact
from Plan 07-01. This module adds routing/policy metadata without changing any
model-visible name, description, schema, or read/write annotation.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:  # Support both ``import registry`` in package-local tests and package imports.
    from .errors import RegistryError
except ImportError:  # pragma: no cover - exercised by direct package-path imports
    from errors import RegistryError


BASELINE_PATH = Path(__file__).resolve().parents[1] / "contracts" / "tool-registry-baseline.json"
RESULT_SCHEMA_VERSION = "1.0"
FORBIDDEN_ARGUMENT_NAMES = frozenset(
    {
        "actor_id",
        "api_key",
        "authorization",
        "client_secret",
        "credentials",
        "database_url",
        "file_path",
        "filesystem_path",
        "farmer_id",
        "internal_actor",
        "password",
        "path",
        "private_key",
        "secret",
        "session_token",
        "sql",
        "tenant_id",
        "token",
    }
)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    access: str
    annotations: dict[str, bool]
    capabilities: tuple[str, ...]
    input_schema: dict[str, Any]
    workflow_tags: frozenset[str]
    required_provider_capabilities: frozenset[str]
    effect_class: str
    confirmation_required: bool
    risk_level: str
    result_schema_version: str = RESULT_SCHEMA_VERSION

    @property
    def read_only(self) -> bool:
        return self.access == "read"

    def baseline_record(self) -> dict[str, Any]:
        return {
            "access": self.access,
            "annotations": copy.deepcopy(self.annotations),
            "capabilities": list(self.capabilities),
            "description": self.description,
            "input_schema": copy.deepcopy(self.input_schema),
            "name": self.name,
        }

    def model_schema(self) -> dict[str, Any]:
        """Return only fields safe to expose to an LLM/provider adapter."""

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": copy.deepcopy(self.input_schema),
            "annotations": copy.deepcopy(self.annotations),
        }

    def metadata(self) -> dict[str, Any]:
        return {
            "workflow_tags": sorted(self.workflow_tags),
            "required_provider_capabilities": sorted(self.required_provider_capabilities),
            "effect_class": self.effect_class,
            "confirmation_required": self.confirmation_required,
            "risk_level": self.risk_level,
            "result_schema_version": self.result_schema_version,
        }


def _load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise RegistryError("The frozen tool contract is unavailable.", code="registry_contract_missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError("The frozen tool contract is invalid.", code="registry_contract_invalid") from exc
    tools = payload.get("tools")
    if not isinstance(tools, list) or len(tools) != 78:
        raise RegistryError("The frozen tool contract does not contain the required inventory.", code="registry_inventory_invalid")
    if payload.get("counts") != {"read": 56, "write": 22}:
        raise RegistryError("The frozen tool contract has an unexpected read/write split.", code="registry_counts_invalid")
    return payload


def _walk_schema_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_schema_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_schema_keys(item)


def _validate_model_schema(name: str, schema: dict[str, Any]) -> None:
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise RegistryError(f"Tool {name} must reject unknown arguments.", code="registry_schema_invalid")
    properties = schema.get("properties", {})
    forbidden = {key.casefold() for key in _walk_schema_keys(properties)} & FORBIDDEN_ARGUMENT_NAMES
    if forbidden:
        raise RegistryError(f"Tool {name} contains a forbidden model argument.", code="registry_identity_argument")


_EXTERNAL_COMPUTE = frozenset(
    {
        "ask_farm_advisor",
        "calculate_profit",
        "check_scheme_eligibility",
        "compare_logistics_options",
        "compare_machinery_costs",
        "compare_marketplace_quotes",
        "compare_mandis",
        "diagnose_crop",
        "recommend_fertilizers",
        "recommend_seeds",
        "send_voice_turn",
        "synthesize_speech",
        "transcribe_audio",
        "translate_text",
    }
)
_PERSISTENT_WRITES = frozenset(
    {
        "create_advisor_session",
        "create_field",
        "create_field_task",
        "create_reminder",
        "create_report",
        "record_irrigation_event",
        "record_ledger_entry",
        "record_sensor_reading",
        "record_soil_test",
        "start_crop_cycle",
        "update_alert_status",
        "update_crop_stage",
        "update_field",
        "update_field_task_status",
        "update_ledger_entry_status",
        "update_profile",
    }
)


def _metadata(name: str, access: str) -> tuple[frozenset[str], frozenset[str], str, bool, str]:
    tags: set[str] = set()
    if name in {"get_farm_overview", "get_component_health", "get_profile", "list_fields", "get_farm_map", "list_alerts", "list_reminders", "list_field_tasks", "get_ledger_summary"}:
        tags.add("farm_context")
    if name in {"get_field", "get_field_timeline", "get_crop_stage_action_proposals", "get_soil_health", "get_latest_field_observations", "list_device_health", "get_weather_for_field", "get_weather_alerts_for_field", "get_irrigation_advice", "list_irrigation_events", "get_crop_options"}:
        tags.update({"field_context", "crop_planning"})
    if name in {"get_crop_options", "get_crop", "list_crops", "recommend_seeds", "recommend_fertilizers", "get_msp", "compare_msp_with_market", "get_market_summary", "get_market_price", "get_nearby_mandi_prices", "get_market_trend", "get_market_history", "compare_mandis", "calculate_profit"}:
        tags.add("crop_planning")
    if name in {"diagnose_crop", "get_soil_health", "get_latest_field_observations", "get_weather_for_field", "get_weather_alerts_for_field", "get_field", "list_fields"}:
        tags.add("crop_health")
    if name in {"find_government_schemes", "list_government_schemes", "get_scheme_details", "check_scheme_eligibility", "query_support_catalog", "list_machinery_rentals", "find_machinery", "find_nearby_machinery", "search_marketplace_listings", "find_nearby_marketplace_listings", "get_marketplace_status", "find_seed_suppliers", "find_fertilizer_suppliers", "find_logistics_providers", "find_crop_buyers", "find_exporters", "compare_marketplace_quotes", "compare_machinery_costs", "compare_logistics_options", "calculate_logistics_cost"}:
        tags.add("support_market")
    if name in {"create_advisor_session", "ask_farm_advisor"}:
        tags.add("advisor")
    if name in {"send_voice_turn", "transcribe_audio", "synthesize_speech", "translate_text"}:
        tags.add("voice")
    if name in _PERSISTENT_WRITES:
        tags.add("record_update")
    if not tags:
        tags.add("farm_context")

    required = {"text_input"}
    if name == "diagnose_crop":
        required.add("image_input")
    if name in {"send_voice_turn", "transcribe_audio"}:
        required.add("audio_input")
    if name == "synthesize_speech":
        required.add("text_to_speech")
    if name == "translate_text":
        required.add("translation")
    if name in {"ask_farm_advisor", "create_advisor_session"}:
        required.add("advisor")

    effect = "authoritative_persistence" if name in _PERSISTENT_WRITES else "external_compute" if name in _EXTERNAL_COMPUTE else "pure_read"
    confirmation = effect == "authoritative_persistence"
    risk = "high" if name in {"diagnose_crop", "update_profile", "update_field"} else "medium" if confirmation else "low"
    return frozenset(tags), frozenset(required), effect, confirmation, risk


def build_registry(path: Path = BASELINE_PATH) -> tuple[ToolDefinition, ...]:
    payload = _load_baseline(path)
    definitions: list[ToolDefinition] = []
    names: set[str] = set()
    for record in payload["tools"]:
        name = str(record.get("name", ""))
        if not name or name in names:
            raise RegistryError("The tool registry contains duplicate or empty names.", code="registry_duplicate_name")
        names.add(name)
        schema = copy.deepcopy(record.get("input_schema", {}))
        _validate_model_schema(name, schema)
        tags, required, effect, confirmation, risk = _metadata(name, str(record["access"]))
        definitions.append(
            ToolDefinition(
                name=name,
                description=str(record["description"]),
                access=str(record["access"]),
                annotations=copy.deepcopy(record["annotations"]),
                capabilities=tuple(record.get("capabilities", [])),
                input_schema=schema,
                workflow_tags=tags,
                required_provider_capabilities=required,
                effect_class=effect,
                confirmation_required=confirmation,
                risk_level=risk,
            )
        )
    if len(definitions) != 78 or sum(item.read_only for item in definitions) != 56 or sum(not item.read_only for item in definitions) != 22:
        raise RegistryError("The canonical tool registry failed its 78/56/22 parity check.", code="registry_parity_invalid")
    return tuple(definitions)


TOOL_REGISTRY = build_registry()
_BY_NAME = {tool.name: tool for tool in TOOL_REGISTRY}


def get_tool(name: str) -> ToolDefinition:
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise RegistryError("Unknown tool.", code="unknown_tool") from exc


def registry_snapshot() -> dict[str, Any]:
    """Return the frozen baseline unchanged, for byte-for-byte parity tests."""

    return _load_baseline()


def metadata_snapshot() -> dict[str, dict[str, Any]]:
    return {tool.name: tool.metadata() for tool in TOOL_REGISTRY}


def model_visible_tools(tool_names: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Expose an explicit allowlist; an omitted list exposes no tools."""

    if tool_names is None:
        return []
    return [get_tool(name).model_schema() for name in tool_names]


def validate_registry() -> None:
    for tool in TOOL_REGISTRY:
        _validate_model_schema(tool.name, tool.input_schema)
        if tool.effect_class == "authoritative_persistence" and not tool.confirmation_required:
            raise RegistryError("Persistent tools must require confirmation.", code="registry_confirmation_invalid")


validate_registry()
