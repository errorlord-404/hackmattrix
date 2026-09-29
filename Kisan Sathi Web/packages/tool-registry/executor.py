"""Provider-neutral execution of canonical KisanSathi tools."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

try:
    from .api_client import ApiClient, BackendResponse, ExecutionContext, idempotency_key
    from .errors import BackendError, PolicyError, ToolValidationError
    from .policy import DEFAULT_POLICY, WorkflowPolicy
    from .registry import TOOL_REGISTRY, ToolDefinition, get_tool
    from .result import DEFAULT_MAX_RESPONSE_BYTES, tool_degraded, tool_error, tool_result, write_action
except ImportError:  # pragma: no cover - direct package-path imports
    from api_client import ApiClient, BackendResponse, ExecutionContext, idempotency_key
    from errors import BackendError, PolicyError, ToolValidationError
    from policy import DEFAULT_POLICY, WorkflowPolicy
    from registry import TOOL_REGISTRY, ToolDefinition, get_tool
    from result import DEFAULT_MAX_RESPONSE_BYTES, tool_degraded, tool_error, tool_result, write_action


def _encoded(value: Any) -> str:
    return quote(str(value), safe="")


def _compact_payload(arguments: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    return {key: arguments[key] for key in keys if key in arguments and arguments[key] is not None}


def _as_number(value: Any, *, label: str, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ToolValidationError(f"{label} must be numeric.", code="invalid_tool_argument") from exc
    if number != number or number in {float("inf"), float("-inf")}:
        raise ToolValidationError(f"{label} must be finite.", code="invalid_tool_argument")
    return number


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.casefold() in {"true", "1", "yes"}:
            return True
        if value.casefold() in {"false", "0", "no"}:
            return False
    raise ToolValidationError("Boolean tool arguments must be true or false.", code="invalid_tool_argument")


def _as_list(value: Any, *, label: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ToolValidationError(f"{label} must be a JSON array.", code="invalid_tool_argument") from exc
        if isinstance(parsed, list):
            return parsed
    raise ToolValidationError(f"{label} must be an array.", code="invalid_tool_argument")


def _as_dict(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ToolValidationError(f"{label} must be a JSON object.", code="invalid_tool_argument") from exc
        if isinstance(parsed, dict):
            return parsed
    raise ToolValidationError(f"{label} must be an object.", code="invalid_tool_argument")


def _decode_base64(value: Any, *, label: str, max_bytes: int) -> bytes:
    if not isinstance(value, str):
        raise ToolValidationError(f"{label} must be base64 text.", code="invalid_tool_argument")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ToolValidationError(f"{label} is not valid base64.", code=f"invalid_{label}") from exc
    if not decoded or len(decoded) > max_bytes:
        raise ToolValidationError(f"{label} must be between 1 byte and the configured limit.", code=f"invalid_{label}_size")
    return decoded


class ToolExecutor:
    """Validate, authorize, and execute one tool inside a trusted turn context."""

    def __init__(
        self,
        client: ApiClient,
        *,
        policy: WorkflowPolicy = DEFAULT_POLICY,
        registry: tuple[ToolDefinition, ...] = TOOL_REGISTRY,
        max_response_bytes: int | None = None,
        max_media_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self.client = client
        self.policy = policy
        self.registry = registry
        self.max_response_bytes = max_response_bytes or client.max_response_bytes or DEFAULT_MAX_RESPONSE_BYTES
        self.max_media_bytes = max_media_bytes
        self._names = {tool.name for tool in registry}

    def _validate_arguments(self, definition: ToolDefinition, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise ToolValidationError("Tool arguments must be an object.", code="invalid_tool_arguments")
        properties = set(definition.input_schema.get("properties", {}))
        unknown = set(arguments) - properties
        if unknown:
            raise ToolValidationError("The tool received an unsupported argument.", code="unknown_tool_argument")
        # Baseline schemas intentionally preserve the MCP shape but do not expose
        # server-only actor/credential/path fields. Enforce that invariant again
        # at execution time in case a caller supplies a hand-built definition.
        for key in arguments:
            if str(key).casefold() in {"farmer_id", "tenant_id", "authorization", "api_key", "secret", "token", "path", "sql"}:
                raise ToolValidationError("Server identity and control arguments are not model inputs.", code="forbidden_tool_argument")
        return dict(arguments)

    @staticmethod
    def _approved(approval: Any) -> bool:
        if approval is True:
            return True
        if isinstance(approval, Mapping):
            return approval.get("accepted") is True or approval.get("status") in {"accepted", "approved", "confirmed"}
        return bool(getattr(approval, "accepted", False)) or getattr(approval, "status", None) in {"accepted", "approved", "confirmed"}

    async def execute(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        context: ExecutionContext,
        *,
        workflow: str,
        approval: Any = None,
    ) -> dict[str, Any]:
        """Execute one normalized call; unknown or unsafe calls fail closed."""

        try:
            if not isinstance(context, ExecutionContext):
                raise ToolValidationError("An authenticated execution context is required.", code="execution_context_required")
            definition = get_tool(tool_name)
            normalized = self._validate_arguments(definition, arguments)
            decision = self.policy.authorize(workflow, tool_name, normalized)
            if decision.confirmation_required and not self._approved(approval):
                return tool_result(
                    status="needs_approval",
                    summary="This farmer-state change requires explicit confirmation before it is saved.",
                    data={"tool": tool_name, "confirmation_required": True, "risk_level": decision.risk_level},
                    request_id=context.request_id,
                    max_response_bytes=self.max_response_bytes,
                )
            return await self._dispatch(definition, normalized, context)
        except (PolicyError, ToolValidationError) as exc:
            return tool_error(
                summary=exc.message,
                code=exc.code,
                retryable=exc.retryable,
                request_id=getattr(context, "request_id", None),
                max_response_bytes=self.max_response_bytes,
            )
        except BackendError as exc:
            return tool_error(
                summary=exc.message,
                code=exc.code,
                retryable=exc.retryable,
                request_id=exc.request_id or context.request_id,
                max_response_bytes=self.max_response_bytes,
            )
        except (KeyError, TypeError, ValueError) as exc:
            # Do not serialize ``exc``: provider/HTTP implementations may put
            # secrets or response bodies in exception text.
            return tool_error(
                summary="The tool arguments could not be normalized safely.",
                code="invalid_tool_argument",
                retryable=False,
                request_id=getattr(context, "request_id", None),
                max_response_bytes=self.max_response_bytes,
            )

    async def _read(self, summary: str, response: BackendResponse, context: ExecutionContext) -> dict[str, Any]:
        return tool_result(
            status="ok",
            summary=summary,
            data=response.data,
            request_id=response.request_id or context.request_id,
            max_response_bytes=self.max_response_bytes,
        )

    async def _write(self, summary: str, path: str, method: str, payload: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        key = idempotency_key(context.actor, self._active_tool, path, payload)
        if method == "PUT":
            response = await self.client.put(path, context=context, json_body=payload, idempotency=key)
        elif method == "PATCH":
            response = await self.client.patch(path, context=context, json_body=payload, idempotency=key)
        else:
            response = await self.client.post(path, context=context, json_body=payload, idempotency=key)
        return tool_result(
            status="ok",
            summary=summary,
            data=response.data,
            request_id=response.request_id or context.request_id,
            action=write_action(path, method, response.data),
            max_response_bytes=self.max_response_bytes,
        )

    async def _get(self, path: str, context: ExecutionContext, *, params: Mapping[str, Any] | None = None, summary: str) -> dict[str, Any]:
        return await self._read(summary, await self.client.get(path, context=context, params=params), context)

    async def _post_read(self, path: str, payload: Any, context: ExecutionContext, *, summary: str) -> dict[str, Any]:
        key = idempotency_key(context.actor, self._active_tool, path, payload)
        return await self._read(summary, await self.client.post(path, context=context, json_body=payload, idempotency=key), context)

    async def _dispatch(self, definition: ToolDefinition, args: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        self._active_tool = definition.name
        name = definition.name

        static_gets: dict[str, tuple[str, str]] = {
            "get_farm_overview": ("/v1/dashboard", "Farm overview loaded."),
            "get_component_health": ("/v1/diagnostics", "Farm service component health loaded; degraded providers remain explicit."),
            "get_profile": ("/v1/profile", "Farmer profile loaded."),
            "get_farm_map": ("/v1/fields/map", "Farm map fields loaded."),
            "list_reminders": ("/v1/reminders", "Farm reminders loaded."),
            "get_ledger_summary": ("/v1/ledger/summary", "Farm ledger summary loaded from active farmer-entered INR records; it is not a financial forecast."),
            "list_reports": ("/v1/reports", "Farm reports loaded."),
            "list_crops": ("/crops", "Crop reference catalog loaded."),
            "list_government_schemes": ("/gov-schemes", "Government scheme catalog loaded."),
            "get_marketplace_status": ("/marketplace/status", "Marketplace directory setup status loaded. A configured source still needs a successful ingestion before it has listings."),
        }
        if name in static_gets:
            path, summary = static_gets[name]
            return await self._get(path, context, summary=summary)

        if name == "list_fields":
            return await self._get("/v1/fields", context, params={"include_inactive": _as_bool(args.get("include_inactive"), False)}, summary="Farm fields loaded.")
        if name == "get_field":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}", context, summary="Field details loaded.")
        if name == "get_field_timeline":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}/timeline", context, summary="Field crop timeline loaded.")
        if name == "get_crop_stage_action_proposals":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}/action-proposals", context, summary="Stage-aware task proposals loaded. They are suggestions only and require farmer confirmation before a task is created.")
        if name == "get_soil_health":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}/soil-health", context, summary="Soil health screening loaded.")
        if name == "get_latest_field_observations":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}/observations/latest", context, summary="Latest field observations loaded.")
        if name == "list_device_health":
            return await self._get("/v1/device-ingestion/devices", context, params={"field_id": args.get("field_id")}, summary="Device freshness and latest packet status loaded. This tool cannot provision a device or control equipment.")
        if name == "get_weather_for_field":
            field = await self.client.get(f"/v1/fields/{_encoded(args['field_id'])}", context=context)
            record = field.data if isinstance(field.data, Mapping) else {}
            latitude, longitude = record.get("centroid_lat"), record.get("centroid_lon")
            if latitude is None or longitude is None:
                return tool_degraded(summary="Weather cannot be loaded because this field has no usable location.", data={"field_id": args["field_id"]}, warning="Add a field boundary or coordinates before requesting field weather.", request_id=field.request_id, max_response_bytes=self.max_response_bytes)
            weather = await self.client.get("/v1/weather", context=context, params={"lat": latitude, "lon": longitude})
            return await self._read("Field weather loaded using the field's stored coordinates.", BackendResponse({"field_id": args["field_id"], "weather": weather.data}, weather.request_id, weather.status_code), context)
        if name == "get_weather_alerts_for_field":
            return await self._get("/v1/weather/alerts", context, params={"field_id": args["field_id"]}, summary="Weather alerts loaded for the field.")
        if name == "get_irrigation_advice":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}/irrigation-plan", context, summary="Irrigation screening advice loaded. No pump or valve was activated.")
        if name == "get_crop_options":
            return await self._get(f"/v1/fields/{_encoded(args['field_id'])}/crop-options", context, params=_compact_payload(args, "season", "previous_crop", "soil_type"), summary="Sourced crop options loaded. These are evidence comparisons, not a profit prediction.")
        if name == "list_irrigation_events":
            limit = _as_number(args.get("limit"), label="limit", default=30)
            return await self._get("/v1/irrigation-events", context, params={"field_id": args.get("field_id"), "limit": min(max(int(limit or 30), 1), 200)}, summary="Farmer-recorded irrigation history loaded. It does not prove delivered water volume.")
        if name == "list_alerts":
            return await self._get("/v1/alerts", context, params={"status": args.get("status")}, summary="Farm alerts loaded.")
        if name == "list_field_tasks":
            return await self._get("/v1/tasks", context, params={"field_id": args.get("field_id"), "status": args.get("status", "open")}, summary="Farmer-confirmed field tasks loaded.")
        if name == "list_ledger_entries":
            return await self._get("/v1/ledger/entries", context, params={"field_id": args.get("field_id"), "entry_type": args.get("entry_type"), "status": args.get("status", "active")}, summary="Farmer-entered ledger records loaded. These records do not execute a payment or determine credit.")
        if name == "get_report":
            return await self._get(f"/v1/reports/{_encoded(args['report_id'])}", context, summary="Farm report loaded.")

        if name in {"get_market_summary", "get_market_price", "get_nearby_mandi_prices"}:
            params = {"crop": args.get("crop", args.get("crop_name")), "district": args.get("district"), "state": args.get("state")}
            return await self._get("/market-prices/summary", context, params=params, summary="Latest market-price summary loaded.")
        if name in {"get_market_trend", "get_market_history"}:
            days = _as_number(args.get("days"), label="days", default=7 if name == "get_market_trend" else 30)
            return await self._get("/market-prices/trend" if name == "get_market_trend" else "/market-prices/history", context, params={"crop": args.get("crop"), "mandi": args.get("mandi"), "days": min(max(int(days or 1), 1), 365)}, summary="Market-price trend loaded." if name == "get_market_trend" else "Market-price history loaded.")
        if name == "compare_mandis":
            quantity = _as_number(args.get("quantity_quintals"), label="quantity_quintals", default=1)
            return await self._get(f"/market-prices/compare/{_encoded(args['crop_name'])}", context, params={"farmer_district": args["farmer_district"], "farmer_state": args["farmer_state"], "quantity_quintals": quantity}, summary="Mandi comparison loaded. Costs and assumptions are returned by the backend.")
        if name == "get_msp":
            return await self._get(f"/msp/by-crop/{_encoded(args['crop_name'])}", context, summary="Minimum support price records loaded.")
        if name == "compare_msp_with_market":
            return await self._get("/msp/compare-market", context, params={"crop": args["crop_name"]}, summary="MSP-to-market comparison loaded. It is not a procurement or eligibility guarantee.")

        if name == "find_government_schemes":
            return await self._get(f"/gov-schemes/by-state/{_encoded(args['state'])}", context, summary="Government schemes for the requested state loaded.")
        if name == "get_scheme_details":
            return await self._get(f"/gov-schemes/{_encoded(args['scheme_id'])}", context, summary="Government scheme details loaded from the reference catalog.")
        if name == "get_crop":
            return await self._get(f"/crops/{_encoded(args['crop_id'])}", context, summary="Crop reference record loaded.")
        if name == "recommend_seeds":
            payload = _compact_payload(args, "crop", "preferred_zone", "disease_risk")
            return await self._post_read("/seeds/recommend", payload, context, summary="Seed recommendations loaded from the reference backend.")
        if name == "recommend_fertilizers":
            payload = _compact_payload(args, "crop_name", "fertilizer_type", "max_budget_per_bag")
            return await self._post_read("/fertilizer/recommend", payload, context, summary="Fertilizer recommendations loaded from the reference backend.")
        if name == "check_scheme_eligibility":
            payload = {"farmer_state": args["farmer_state"], "eligibility_criteria": _as_list(args.get("eligibility_criteria"), label="eligibility_criteria")}
            return await self._post_read("/gov-schemes/check-eligibility", payload, context, summary="Government-scheme eligibility results loaded.")

        if name in {"list_machinery_rentals", "find_machinery"}:
            return await self._get("/machinery-rentals", context, params=_compact_payload(args, "category", "district", "state"), summary="Machinery rental listings loaded.")
        if name == "find_nearby_machinery":
            return await self._nearby(context, args, listing="machinery")
        if name == "search_marketplace_listings":
            limit = _as_number(args.get("limit"), label="limit", default=30)
            return await self._get("/marketplace/listings", context, params={**_compact_payload(args, "listing_type", "category", "district", "state", "query"), "limit": min(max(int(limit or 30), 1), 100)}, summary="Marketplace directory listings loaded. These are public discovery records, not booking or purchase offers.")
        if name == "find_nearby_marketplace_listings":
            return await self._nearby(context, args, listing="marketplace")
        if name in {"find_seed_suppliers", "find_fertilizer_suppliers", "find_logistics_providers", "find_crop_buyers", "find_exporters"}:
            kind = {"find_seed_suppliers": "seed", "find_fertilizer_suppliers": "fertilizer", "find_logistics_providers": "logistics", "find_crop_buyers": "buyer", "find_exporters": "exporter"}[name]
            return await self._get("/marketplace/listings", context, params={"listing_type": kind, **_compact_payload(args, "district", "state", "query")}, summary="Source-attributed marketplace directory listings loaded. These are discovery-only records.")
        if name in {"compare_marketplace_quotes", "compare_machinery_costs", "compare_logistics_options"}:
            return await self._post_read("/marketplace/compare-quotes", {"quotes": _as_list(args.get("quotes"), label="quotes")}, context, summary="Quote comparison completed from the supplied quotes. Verify same currency and unit before choosing.")
        if name == "calculate_logistics_cost":
            return await self._post_read("/marketplace/compare-quotes", {"quotes": [_as_dict(args.get("quote"), label="quote")]}, context, summary="Logistics cost calculated from the supplied quote.")
        if name == "query_support_catalog":
            return await self._query_support_catalog(args, context)

        # Keep path parameters as templates. Building this map must not read
        # arguments for unrelated tools (for example ``create_field`` has no
        # ``field_id``), otherwise a valid write fails before dispatch.
        writes: dict[str, tuple[str, str, tuple[str, ...], str]] = {
            "update_field": ("PATCH", "/v1/fields/{field_id}", ("name", "area_acres", "boundary_geojson", "current_crop", "active"), "Field updated."),
            "create_field_task": ("POST", "/v1/tasks", ("field_id", "title", "due_at", "source"), "Farmer-confirmed field task created."),
            "update_field_task_status": ("PATCH", "/v1/tasks/{task_id}", ("status",), "Farmer-confirmed field task updated."),
            "record_ledger_entry": ("POST", "/v1/ledger/entries", ("field_id", "entry_type", "category", "title", "amount_inr", "occurred_at", "crop_name", "note", "source"), "Farmer-confirmed ledger record saved. No payment, credit, or transfer was made."),
            "update_ledger_entry_status": ("PATCH", "/v1/ledger/entries/{entry_id}", ("status",), "Ledger record status updated; voided records remain in history for audit."),
            "create_field": ("POST", "/v1/fields", ("name", "area_acres", "boundary_geojson", "current_crop"), "Field created."),
            "start_crop_cycle": ("POST", "/v1/fields/{field_id}/crop-cycles", ("crop_name", "planted_at", "expected_harvest_date", "initial_stage"), "Crop cycle started."),
            "update_crop_stage": ("PATCH", "/v1/crop-cycles/{cycle_id}/stage", ("stage", "occurred_at", "note"), "Crop stage updated."),
            "record_soil_test": ("POST", "/v1/fields/{field_id}/soil-tests", ("observed_at", "ph", "organic_carbon", "nitrogen", "phosphorus", "potassium", "ec", "moisture_percent", "source", "confidence"), "Soil test recorded."),
            "update_alert_status": ("PATCH", "/v1/alerts/{alert_id}", ("status",), "Alert status updated."),
            "record_sensor_reading": ("POST", "/v1/sensor-readings", ("field_id", "device_id", "measurement", "value", "unit", "observed_at", "source", "confidence"), "Sensor reading recorded."),
            "create_advisor_session": ("POST", "/v1/advisor/sessions", ("field_id", "language"), "Advisor session created."),
            "record_irrigation_event": ("POST", "/v1/irrigation-events", ("field_id", "occurred_at", "volume_liters", "duration_minutes", "method", "note"), "Irrigation event recorded. No pump or valve was controlled."),
            "create_reminder": ("POST", "/v1/reminders", ("field_id", "reminder_type", "scheduled_for", "title"), "Reminder created."),
            "create_report": ("POST", "/v1/reports", ("report_type", "from_date", "to_date"), "Farm report created."),
            "update_profile": ("PUT", "/v1/profile", ("name", "phone", "location", "preferred_language", "latitude", "longitude"), "Farmer profile updated."),
        }
        if name in writes:
            method, path_template, keys, summary = writes[name]
            path = path_template
            for path_key in ("field_id", "task_id", "entry_id", "cycle_id", "alert_id"):
                placeholder = "{" + path_key + "}"
                if placeholder in path:
                    path = path.replace(placeholder, _encoded(args[path_key]))
            payload = _compact_payload(args, *keys)
            if name == "update_profile":
                payload["notification_preferences"] = {"enabled": _as_bool(args.get("notifications_enabled"), True), "channels": args.get("notification_channels") or ["in_app"]}
            if name == "record_ledger_entry":
                amount = _as_number(payload.get("amount_inr"), label="amount_inr")
                if amount is None or amount <= 0:
                    raise ToolValidationError("A ledger amount must be greater than zero.", code="invalid_ledger_amount")
                if payload.get("entry_type") not in {"income", "expense"}:
                    raise ToolValidationError("entry_type must be income or expense.", code="invalid_ledger_entry_type")
                payload["amount_inr"] = amount
            return await self._write(summary, path, method, payload, context)

        if name == "ask_farm_advisor":
            session_id = args.get("session_id")
            if not session_id:
                session_payload = {"field_id": args.get("field_id"), "language": args.get("language", "en")}
                session = await self.client.post("/v1/advisor/sessions", context=context, json_body=session_payload, idempotency=idempotency_key(context.actor, name, "/v1/advisor/sessions", session_payload))
                if not isinstance(session.data, Mapping) or not session.data.get("id"):
                    raise ToolValidationError("The advisor returned an invalid session response.", code="advisor_invalid_response")
                session_id = session.data["id"]
            path = f"/v1/advisor/sessions/{_encoded(session_id)}/messages"
            payload = {"content": args["content"]}
            response = await self.client.post(path, context=context, json_body=payload, idempotency=idempotency_key(context.actor, name, path, payload))
            return await self._read("Farm advisor response loaded. Provider availability and citations are preserved in the response.", BackendResponse({"session_id": session_id, "message": response.data}, response.request_id, response.status_code), context)
        if name == "diagnose_crop":
            return await self._diagnose(args, context)
        if name == "send_voice_turn":
            audio = _decode_base64(args["audio_base64"], label="audio_base64", max_bytes=self.max_media_bytes)
            response = await self.client.post_bytes("/v1/voice/turns", context=context, content=audio, content_type=args.get("mime_type", "audio/webm"))
            return await self._read("Voice turn result loaded. Provider-unavailable states are preserved.", response, context)
        if name == "transcribe_audio":
            audio = _decode_base64(args["audio_base64"], label="audio_base64", max_bytes=self.max_media_bytes)
            response = await self.client.post_bytes("/v1/voice/transcribe", context=context, content=audio, content_type=args.get("mime_type", "audio/webm"), params={"language_code": args.get("language_code")})
            return await self._read("Speech transcription result loaded; provider-unavailable states are preserved.", response, context)
        if name == "synthesize_speech":
            payload = _compact_payload(args, "text", "language_code", "speaker", "model", "pace")
            return await self._read("Speech synthesis result loaded; audio remains base64 encoded.", await self.client.post("/v1/voice/synthesize", context=context, json_body=payload, idempotency=idempotency_key(context.actor, name, "/v1/voice/synthesize", payload)), context)
        if name == "translate_text":
            payload = {"input": args["text"], **_compact_payload(args, "source_language_code", "target_language_code", "model", "mode")}
            return await self._read("Translation result loaded; source and target language codes are preserved.", await self.client.post("/v1/translate", context=context, json_body=payload, idempotency=idempotency_key(context.actor, name, "/v1/translate", payload)), context)
        if name == "calculate_profit":
            return self._calculate_profit(args, context)
        raise ToolValidationError("The registered tool has no safe executor route.", code="tool_route_missing")

    async def _nearby(self, context: ExecutionContext, args: dict[str, Any], *, listing: str) -> dict[str, Any]:
        field = await self.client.get(f"/v1/fields/{_encoded(args['field_id'])}", context=context)
        record = field.data if isinstance(field.data, Mapping) else {}
        latitude, longitude = record.get("centroid_lat"), record.get("centroid_lon")
        if latitude is None or longitude is None:
            return tool_degraded(summary=f"Nearby {listing} listings are unavailable because this field has no recorded coordinates.", data=[], warning="Add or select a field location before requesting nearby providers.", request_id=field.request_id, max_response_bytes=self.max_response_bytes)
        radius = _as_number(args.get("radius_km"), label="radius_km", default=25)
        path = "/machinery-rentals/nearby" if listing == "machinery" else "/marketplace/nearby"
        params = {"lat": latitude, "lon": longitude, "radius_km": min(max(radius or 25, 1), 250)}
        params["category" if listing == "machinery" else "listing_type"] = args.get("category" if listing == "machinery" else "listing_type")
        return await self._get(path, context, params=params, summary=f"Nearby {listing} listings loaded for the selected field.")

    async def _query_support_catalog(self, args: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        include_schemes = _as_bool(args.get("include_schemes"), True)
        include_machinery = _as_bool(args.get("include_machinery"), True)
        include_marketplace = _as_bool(args.get("include_marketplace"), True)
        if not (include_schemes or include_machinery or include_marketplace):
            raise ToolValidationError("Select at least one support catalog to query.", code="no_support_catalog_selected")
        limit = _as_number(args.get("limit"), label="limit", default=10)
        bounded_limit = min(max(int(limit or 10), 1), 50)
        calls: dict[str, Any] = {}
        if include_schemes:
            calls["schemes"] = self.client.get(f"/gov-schemes/by-state/{_encoded(args['state'])}" if args.get("state") else "/gov-schemes", context=context)
        if include_machinery:
            calls["machinery"] = self.client.get("/machinery-rentals", context=context, params={"district": args.get("district"), "state": args.get("state")})
        if include_marketplace:
            calls["marketplace"] = self.client.get("/marketplace/listings", context=context, params={"category": args.get("category"), "district": args.get("district"), "state": args.get("state"), "query": args.get("query"), "limit": bounded_limit})
        responses = await asyncio.gather(*calls.values(), return_exceptions=True)
        data: dict[str, Any] = {}
        warnings: list[str] = []
        request_id = context.request_id
        for (label, _), response in zip(calls.items(), responses):
            if isinstance(response, BackendError):
                warnings.append(f"{label} catalog unavailable.")
                continue
            if isinstance(response, Exception):
                warnings.append(f"{label} catalog unavailable.")
                continue
            request_id = response.request_id or request_id
            value = response.data
            data[label] = value[:bounded_limit] if isinstance(value, list) else value
        return tool_result(status="degraded" if warnings else "ok", summary="Support catalogs loaded for the farmer's prompt. Records are discovery-only and source-attributed.", data={"filters": _compact_payload(args, "state", "district", "category", "query"), "results": data}, request_id=request_id, warnings=warnings, max_response_bytes=self.max_response_bytes)

    async def _diagnose(self, args: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        mime_type = args.get("mime_type", "image/jpeg")
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime_type)
        if suffix is None:
            raise ToolValidationError("Only JPEG, PNG, and WebP crop images are accepted.", code="invalid_image_type")
        image = _decode_base64(args["image_base64"], label="image_base64", max_bytes=self.max_media_bytes)
        boundary = "----KisanSathiBoundary"
        chunks = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"crop{suffix}\"\r\nContent-Type: {mime_type}\r\n\r\n".encode(), image]
        for key in ("field_id", "confirmed_crop"):
            if args.get(key) is not None:
                chunks.append(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{args[key]}".encode())
        chunks.append(f"\r\n--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        resource = "/v1/diagnoses"
        key_payload = {"field_id": args.get("field_id"), "confirmed_crop": args.get("confirmed_crop"), "mime_type": mime_type, "sha256": hashlib.sha256(image).hexdigest()}
        response = await self.client.post_bytes(resource, context=context, content=body, content_type=f"multipart/form-data; boundary={boundary}", idempotency=idempotency_key(context.actor, self._active_tool, resource, key_payload))
        return await self._read("Crop diagnosis result loaded. Inconclusive/provider-unavailable states are preserved.", response, context)

    def _calculate_profit(self, args: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        revenue = _as_number(args.get("revenue"), label="revenue", default=0) or 0
        quantity = _as_number(args.get("quantity_quintals"), label="quantity_quintals")
        price = _as_number(args.get("sale_price_per_quintal"), label="sale_price_per_quintal")
        if revenue < 0 or (quantity is not None and quantity < 0) or (price is not None and price < 0):
            return tool_error(summary="Revenue, quantity, and sale price cannot be negative.", code="invalid_finance_input", retryable=False, request_id=context.request_id, max_response_bytes=self.max_response_bytes)
        expenses = _as_list(args.get("expenses"), label="expenses")
        total = 0.0
        breakdown: list[dict[str, Any]] = []
        for item in expenses:
            if not isinstance(item, Mapping):
                return tool_error(summary="Each expense must contain a non-negative numeric amount.", code="invalid_finance_expense", retryable=False, request_id=context.request_id, max_response_bytes=self.max_response_bytes)
            amount = _as_number(item.get("amount"), label="expense amount")
            if amount is None or amount < 0:
                return tool_error(summary="Each expense must contain a non-negative numeric amount.", code="invalid_finance_expense", retryable=False, request_id=context.request_id, max_response_bytes=self.max_response_bytes)
            total += amount
            breakdown.append({"title": str(item.get("title") or "Expense"), "amount": amount})
        modeled_revenue = quantity * price if quantity is not None and price is not None else revenue
        return tool_result(status="ok", summary="Profit calculation completed locally from user-provided assumptions; no financial ledger was persisted.", data={"revenue": modeled_revenue, "expenses": total, "profit": modeled_revenue - total, "expense_breakdown": breakdown, "assumptions": {"quantity_quintals": quantity, "sale_price_per_quintal": price}}, source="local_calculation", request_id=context.request_id, max_response_bytes=self.max_response_bytes)
