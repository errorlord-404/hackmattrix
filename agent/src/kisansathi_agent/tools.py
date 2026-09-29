from __future__ import annotations

import hashlib
import json
import base64
import binascii
import asyncio
from typing import Any
from urllib.parse import quote

from .backend_client import BackendClient, BackendResponse
from .errors import BackendError
from .result import tool_degraded, tool_error, tool_result, write_action


class KisanSathiTools:
    """Task-oriented read tools backed by the existing FastAPI service."""

    def __init__(self, client: BackendClient) -> None:
        self.client = client

    @property
    def max_response_bytes(self) -> int:
        return self.client.settings.max_response_bytes

    async def _read(self, summary: str, call: Any) -> dict[str, Any]:
        try:
            response: BackendResponse = await call
        except BackendError as exc:
            return tool_error(
                summary=exc.message,
                code=exc.code,
                retryable=exc.retryable,
                request_id=exc.request_id,
            )
        return tool_result(
            status="ok",
            summary=summary,
            data=response.data,
            request_id=response.request_id,
            max_response_bytes=self.max_response_bytes,
        )

    @staticmethod
    def _idempotency_key(path: str, payload: dict[str, Any]) -> str:
        body = json.dumps({"path": path, "payload": payload}, sort_keys=True, separators=(",", ":"), default=str)
        return "ks-" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:48]

    async def _write(
        self,
        summary: str,
        path: str,
        payload: dict[str, Any],
        method: str = "POST",
    ) -> dict[str, Any]:
        try:
            key = self._idempotency_key(path, payload)
            if method == "PATCH":
                response = await self.client.patch(path, json=payload, idempotency_key=key)
            elif method == "PUT":
                response = await self.client.put(path, json=payload, idempotency_key=key)
            else:
                response = await self.client.post(path, json=payload, idempotency_key=key)
        except BackendError as exc:
            return tool_error(
                summary=exc.message,
                code=exc.code,
                retryable=exc.retryable,
                request_id=exc.request_id,
            )
        return tool_result(
            status="ok",
            summary=summary,
            data=response.data,
            request_id=response.request_id,
            action=write_action(path, method, response.data),
            max_response_bytes=self.max_response_bytes,
        )

    async def get_farm_overview(self) -> dict[str, Any]:
        return await self._read("Farm overview loaded.", self.client.get("/v1/dashboard"))

    async def get_component_health(self) -> dict[str, Any]:
        return await self._read(
            "Farm service component health loaded; degraded providers remain explicit.",
            self.client.get("/v1/diagnostics"),
        )

    async def get_onboarding_status(self) -> dict[str, Any]:
        return await self._read(
            "Farmer setup status loaded; no records were changed.",
            self.client.get("/v1/onboarding-status"),
        )

    async def get_diagnosis(self, diagnosis_id: str) -> dict[str, Any]:
        return await self._read(
            "Farmer-scoped crop-photo evidence loaded. A model candidate is not a confirmed diagnosis.",
            self.client.get(f"/v1/diagnoses/{quote(diagnosis_id, safe='')}"),
        )

    async def get_profile(self) -> dict[str, Any]:
        return await self._read("Farmer profile loaded.", self.client.get("/v1/profile"))

    async def list_fields(self, include_inactive: bool = False) -> dict[str, Any]:
        return await self._read(
            "Farm fields loaded.",
            self.client.get("/v1/fields", params={"include_inactive": include_inactive}),
        )

    async def get_farm_map(self) -> dict[str, Any]:
        return await self._read("Farm map fields loaded.", self.client.get("/v1/fields/map"))

    async def get_field(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Field details loaded.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}"),
        )

    async def update_field(
        self,
        field_id: str,
        name: str | None = None,
        area_acres: float | None = None,
        boundary_geojson: dict[str, Any] | None = None,
        current_crop: str | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        payload = {
            key: value
            for key, value in {
                "name": name,
                "area_acres": area_acres,
                "boundary_geojson": boundary_geojson,
                "current_crop": current_crop,
                "active": active,
            }.items()
            if value is not None
        }
        return await self._write(
            "Field updated.",
            f"/v1/fields/{quote(field_id, safe='')}",
            payload,
            method="PATCH",
        )

    async def get_field_timeline(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Field crop timeline loaded.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/timeline"),
        )

    async def get_soil_health(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Soil health screening loaded.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/soil-health"),
        )

    async def get_latest_field_observations(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Latest field observations loaded.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/observations/latest"),
        )

    async def get_tomato_demo(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Tomato prototype simulator status and source-labelled observations loaded; simulated values are not hardware or lab evidence.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/tomato-demo"),
        )

    async def get_weather_for_field(self, field_id: str) -> dict[str, Any]:
        try:
            field_response = await self.client.get(f"/v1/fields/{quote(field_id, safe='')}")
            field = field_response.data
            lat = field.get("centroid_lat") if isinstance(field, dict) else None
            lon = field.get("centroid_lon") if isinstance(field, dict) else None
            if lat is None or lon is None:
                return tool_degraded(
                    summary="Weather cannot be loaded because this field has no usable location.",
                    data={"field_id": field_id},
                    warning="Add a field boundary or coordinates before requesting field weather.",
                    request_id=field_response.request_id,
                )
            weather = await self.client.get("/v1/weather", params={"lat": lat, "lon": lon})
        except BackendError as exc:
            return tool_error(
                summary=exc.message,
                code=exc.code,
                retryable=exc.retryable,
                request_id=exc.request_id,
            )
        return tool_result(
            status="ok",
            summary="Field weather loaded using the field's stored coordinates.",
            data={"field_id": field_id, "weather": weather.data},
            request_id=weather.request_id,
            max_response_bytes=self.max_response_bytes,
        )

    async def get_weather_alerts_for_field(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Weather alerts loaded for the field.",
            self.client.get("/v1/weather/alerts", params={"field_id": field_id}),
        )

    async def get_irrigation_advice(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Irrigation screening advice loaded. No pump or valve was activated.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/irrigation-plan"),
        )

    async def get_crop_options(self, field_id: str, season: str, previous_crop: str | None = None, soil_type: str | None = None) -> dict[str, Any]:
        return await self._read(
            "Sourced crop options loaded. These are evidence comparisons, not a profit prediction.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/crop-options", params={"season": season, "previous_crop": previous_crop, "soil_type": soil_type}),
        )

    async def list_irrigation_events(self, field_id: str | None = None, limit: int = 30) -> dict[str, Any]:
        return await self._read(
            "Farmer-recorded irrigation history loaded. It does not prove delivered water volume.",
            self.client.get("/v1/irrigation-events", params={"field_id": field_id, "limit": limit}),
        )

    async def list_alerts(self, status: str | None = None) -> dict[str, Any]:
        return await self._read(
            "Farm alerts loaded.",
            self.client.get("/v1/alerts", params={"status": status}),
        )

    async def list_reminders(self) -> dict[str, Any]:
        return await self._read("Farm reminders loaded.", self.client.get("/v1/reminders"))

    async def list_field_tasks(
        self,
        field_id: str | None = None,
        status: str | None = "open",
    ) -> dict[str, Any]:
        return await self._read(
            "Farmer-confirmed field tasks loaded.",
            self.client.get("/v1/tasks", params={"field_id": field_id, "status": status}),
        )

    async def get_crop_stage_action_proposals(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Stage-aware task proposals loaded. They are suggestions only and require farmer confirmation before a task is created.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/action-proposals"),
        )

    async def list_device_health(self, field_id: str | None = None) -> dict[str, Any]:
        return await self._read(
            "Device freshness and latest packet status loaded. This tool cannot provision a device or control equipment.",
            self.client.get("/v1/device-ingestion/devices", params={"field_id": field_id}),
        )

    async def create_field_task(
        self,
        field_id: str,
        title: str,
        due_at: str | None = None,
        source: str = "farmer_confirmed:agent",
    ) -> dict[str, Any]:
        payload = {"field_id": field_id, "title": title, "due_at": due_at, "source": source}
        return await self._write("Farmer-confirmed field task created.", "/v1/tasks", payload)

    async def update_field_task_status(self, task_id: str, status: str) -> dict[str, Any]:
        return await self._write(
            "Farmer-confirmed field task updated.",
            f"/v1/tasks/{quote(task_id, safe='')}",
            {"status": status},
            method="PATCH",
        )

    async def list_ledger_entries(
        self,
        field_id: str | None = None,
        entry_type: str | None = None,
        status: str | None = "active",
    ) -> dict[str, Any]:
        return await self._read(
            "Farmer-entered ledger records loaded. These records do not execute a payment or determine credit.",
            self.client.get("/v1/ledger/entries", params={"field_id": field_id, "entry_type": entry_type, "status": status}),
        )

    async def get_ledger_summary(self) -> dict[str, Any]:
        return await self._read(
            "Farm ledger summary loaded from active farmer-entered INR records; it is not a financial forecast.",
            self.client.get("/v1/ledger/summary"),
        )

    async def record_ledger_entry(
        self,
        entry_type: str,
        category: str,
        title: str,
        amount_inr: float,
        occurred_at: str,
        field_id: str | None = None,
        crop_name: str | None = None,
        note: str | None = None,
        source: str = "farmer_confirmed:agent",
    ) -> dict[str, Any]:
        if amount_inr <= 0:
            return tool_error(summary="A ledger amount must be greater than zero.", code="invalid_ledger_amount", retryable=False)
        if entry_type not in {"income", "expense"}:
            return tool_error(summary="entry_type must be income or expense.", code="invalid_ledger_entry_type", retryable=False)
        payload = {
            "field_id": field_id, "entry_type": entry_type, "category": category, "title": title,
            "amount_inr": amount_inr, "occurred_at": occurred_at, "crop_name": crop_name,
            "note": note, "source": source,
        }
        return await self._write(
            "Farmer-confirmed ledger record saved. No payment, credit, or transfer was made.",
            "/v1/ledger/entries",
            payload,
        )

    async def update_ledger_entry_status(self, entry_id: str, status: str) -> dict[str, Any]:
        if status not in {"active", "void"}:
            return tool_error(summary="Ledger status must be active or void.", code="invalid_ledger_status", retryable=False)
        return await self._write(
            "Ledger record status updated; voided records remain in history for audit.",
            f"/v1/ledger/entries/{quote(entry_id, safe='')}",
            {"status": status},
            method="PATCH",
        )

    async def list_reports(self) -> dict[str, Any]:
        return await self._read("Farm reports loaded.", self.client.get("/v1/reports"))

    async def get_report(self, report_id: str) -> dict[str, Any]:
        return await self._read(
            "Farm report loaded.",
            self.client.get(f"/v1/reports/{quote(report_id, safe='')}"),
        )

    async def get_market_summary(
        self,
        crop: str | None = None,
        district: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        return await self._read(
            "Latest market-price summary loaded.",
            self.client.get(
                "/market-prices/summary",
                params={"crop": crop, "district": district, "state": state},
            ),
        )

    async def get_market_trend(
        self,
        crop: str,
        mandi: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        return await self._read(
            "Market-price trend loaded.",
            self.client.get("/market-prices/trend", params={"crop": crop, "mandi": mandi, "days": days}),
        )

    async def get_market_history(
        self,
        crop: str | None = None,
        mandi: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        return await self._read(
            "Market-price history loaded.",
            self.client.get("/market-prices/history", params={"crop": crop, "mandi": mandi, "days": days}),
        )

    async def compare_mandis(
        self,
        crop_name: str,
        farmer_district: str,
        farmer_state: str,
        quantity_quintals: float = 1.0,
    ) -> dict[str, Any]:
        return await self._read(
            "Mandi comparison loaded. Costs and assumptions are returned by the backend.",
            self.client.get(
                f"/market-prices/compare/{quote(crop_name, safe='')}",
                params={
                    "farmer_district": farmer_district,
                    "farmer_state": farmer_state,
                    "quantity_quintals": quantity_quintals,
                },
            ),
        )

    async def get_msp(self, crop_name: str) -> dict[str, Any]:
        return await self._read(
            "Minimum support price records loaded.",
            self.client.get(f"/msp/by-crop/{quote(crop_name, safe='')}"),
        )

    async def compare_sale_routes(
        self,
        crop_name: str,
        quantity_quintals: float,
        routes: list[dict[str, Any]],
        grade: str | None = None,
        variety: str | None = None,
        max_price_age_days: int = 7,
    ) -> dict[str, Any]:
        payload = {
            "crop_name": crop_name, "quantity_quintals": quantity_quintals,
            "routes": routes, "grade": grade, "variety": variety,
            "max_price_age_days": max_price_age_days,
        }
        return await self._read(
            "Quote-backed sale-route comparison loaded. A recommendation exists only with fresh comparable prices and complete dated distance/cost evidence.",
            self.client.post(
                "/market-prices/compare-routes", json=payload,
                idempotency_key=self._idempotency_key("/market-prices/compare-routes", payload),
            ),
        )

    async def compare_msp_with_market(self, crop_name: str) -> dict[str, Any]:
        return await self._read(
            "MSP-to-market comparison loaded. It is not a procurement or eligibility guarantee.",
            self.client.get("/msp/compare-market", params={"crop": crop_name}),
        )

    async def get_market_price(self, crop_name: str, district: str | None = None, state: str | None = None) -> dict[str, Any]:
        return await self.get_market_summary(crop=crop_name, district=district, state=state)

    async def get_nearby_mandi_prices(self, crop_name: str, district: str, state: str) -> dict[str, Any]:
        return await self.get_market_summary(crop=crop_name, district=district, state=state)

    async def find_government_schemes(self, state: str) -> dict[str, Any]:
        return await self._read(
            "Government schemes for the requested state loaded.",
            self.client.get(f"/gov-schemes/by-state/{quote(state, safe='')}"),
        )

    async def list_government_schemes(self) -> dict[str, Any]:
        return await self._read("Government scheme catalog loaded.", self.client.get("/gov-schemes"))

    async def get_scheme_details(self, scheme_id: str) -> dict[str, Any]:
        return await self._read(
            "Government scheme details loaded from the reference catalog.",
            self.client.get(f"/gov-schemes/{quote(scheme_id, safe='')}"),
        )

    async def query_support_catalog(
        self,
        state: str | None = None,
        district: str | None = None,
        category: str | None = None,
        query: str | None = None,
        include_schemes: bool = True,
        include_machinery: bool = True,
        include_marketplace: bool = True,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Load bounded support records for one natural-language farmer prompt."""
        bounded_limit = min(max(limit, 1), 50)
        query_text = (query or "").strip().casefold()
        calls: dict[str, Any] = {}
        if include_schemes:
            calls["schemes"] = self.client.get(
                f"/gov-schemes/by-state/{quote(state, safe='')}" if state else "/gov-schemes"
            )
        if include_machinery:
            calls["machinery"] = self.client.get(
                "/machinery-rentals",
                # FARMS vehicle labels vary (for example "tractor" versus
                # "tractor mounted implement"), so keyword matching below is
                # safer than an exact category filter at this boundary.
                params={"district": district, "state": state},
            )
        if include_marketplace:
            calls["marketplace"] = self.client.get(
                "/marketplace/listings",
                params={
                    "category": category,
                    "district": district,
                    "state": state,
                    "query": query,
                    "limit": bounded_limit,
                },
            )
        if not calls:
            return tool_error(
                summary="Select at least one support catalog to query.",
                code="no_support_catalog_selected",
                retryable=False,
            )

        responses = await asyncio.gather(*calls.values(), return_exceptions=True)
        data: dict[str, Any] = {}
        warnings: list[str] = []
        request_ids: list[str] = []

        def compact_record(label: str, item: Any) -> Any:
            if not isinstance(item, dict):
                return item
            fields = {
                "schemes": (
                    "id", "source_record_id", "name", "description", "benefits",
                    "eligibility_criteria", "official_source_url", "applicable_states",
                    "source", "fetched_at",
                ),
                "machinery": (
                    "id", "source_record_id", "record_kind", "name", "category",
                    "provider_name", "location", "district", "state", "latitude",
                    "longitude", "hourly_rate", "daily_rate", "availability_status",
                    "contact_phone", "source", "source_url", "source_status", "fetched_at",
                ),
                "marketplace": (
                    "id", "source_record_id", "record_kind", "listing_type", "title",
                    "category", "provider_name", "location", "district", "state",
                    "latitude", "longitude", "price_amount", "price_currency", "price_unit",
                    "availability_status", "contact_phone", "source", "source_url",
                    "source_status", "fetched_at",
                ),
            }[label]
            result = {key: item[key] for key in fields if key in item and item[key] is not None}
            for key in ("description", "benefits"):
                if isinstance(result.get(key), str) and len(result[key]) > 360:
                    result[key] = result[key][:357].rstrip() + "..."
            if isinstance(result.get("eligibility_criteria"), list):
                result["eligibility_criteria"] = result["eligibility_criteria"][:3]
            return result

        for (label, _), response in zip(calls.items(), responses):
            if isinstance(response, BackendError):
                warnings.append(f"{label} catalog unavailable: {response.message}")
                continue
            if isinstance(response, Exception):
                warnings.append(f"{label} catalog unavailable: the backend request failed")
                continue
            request_ids.append(response.request_id)
            value = response.data
            if label == "machinery" and isinstance(value, list) and (category or query_text):
                terms = [term for term in (category, query) if term and term.strip()]
                value = [
                    item for item in value
                    if any(
                        term.casefold() in " ".join(
                            str(item.get(key, ""))
                            for key in ("name", "category", "provider_name", "description", "location")
                        ).casefold()
                        for term in terms
                    )
                ]
            if label == "schemes" and query_text and isinstance(value, list):
                value = [
                    item for item in value
                    if query_text in " ".join(
                        str(item.get(key, ""))
                        for key in ("name", "description", "benefits", "eligibility_criteria")
                    ).casefold()
                ]
            data[label] = (
                [compact_record(label, item) for item in value[:bounded_limit]]
                if isinstance(value, list)
                else value
            )

        if not data:
            return tool_result(
                status="degraded",
                summary="No support catalog could be loaded for this prompt.",
                data={},
                request_id=request_ids[0] if request_ids else None,
                warnings=warnings or ["The selected support catalogs returned no data."],
                max_response_bytes=self.max_response_bytes,
            )
        return tool_result(
            status="degraded" if warnings else "ok",
            summary="Support catalogs loaded for the farmer's prompt. Records are discovery-only and source-attributed.",
            data={
                "filters": {
                    "state": state,
                    "district": district,
                    "category": category,
                    "query": query,
                    "limit": bounded_limit,
                },
                "results": data,
            },
            request_id=request_ids[0] if request_ids else None,
            warnings=warnings,
            max_response_bytes=self.max_response_bytes,
        )

    async def list_crops(self) -> dict[str, Any]:
        return await self._read("Crop reference catalog loaded.", self.client.get("/crops"))

    async def get_crop(self, crop_id: str) -> dict[str, Any]:
        return await self._read(
            "Crop reference record loaded.",
            self.client.get(f"/crops/{quote(crop_id, safe='')}"),
        )

    async def recommend_seeds(
        self,
        crop: str,
        preferred_zone: str | None = None,
        disease_risk: str | None = None,
    ) -> dict[str, Any]:
        return await self._read(
            "Seed recommendations loaded from the reference backend.",
            self.client.post(
                "/seeds/recommend",
                json={"crop": crop, "preferred_zone": preferred_zone, "disease_risk": disease_risk},
                idempotency_key=self._idempotency_key(
                    "/seeds/recommend",
                    {"crop": crop, "preferred_zone": preferred_zone, "disease_risk": disease_risk},
                ),
            ),
        )

    async def recommend_fertilizers(
        self,
        crop_name: str,
        fertilizer_type: str | None = None,
        max_budget_per_bag: float | None = None,
    ) -> dict[str, Any]:
        return await self._read(
            "Fertilizer recommendations loaded from the reference backend.",
            self.client.post(
                "/fertilizer/recommend",
                json={
                    "crop_name": crop_name,
                    "fertilizer_type": fertilizer_type,
                    "max_budget_per_bag": max_budget_per_bag,
                },
                idempotency_key=self._idempotency_key(
                    "/fertilizer/recommend",
                    {"crop_name": crop_name, "fertilizer_type": fertilizer_type, "max_budget_per_bag": max_budget_per_bag},
                ),
            ),
        )

    async def check_scheme_eligibility(
        self,
        farmer_state: str,
        eligibility_criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {"farmer_state": farmer_state, "eligibility_criteria": eligibility_criteria or []}
        return await self._read(
            "Government-scheme eligibility results loaded.",
            self.client.post(
                "/gov-schemes/check-eligibility",
                json=payload,
                idempotency_key=self._idempotency_key("/gov-schemes/check-eligibility", payload),
            ),
        )

    async def list_machinery_rentals(
        self,
        category: str | None = None,
        district: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        return await self._read(
            "Machinery rental listings loaded.",
            self.client.get(
                "/machinery-rentals",
                params={"category": category, "district": district, "state": state},
            ),
        )

    async def find_machinery(self, category: str | None = None, district: str | None = None, state: str | None = None) -> dict[str, Any]:
        return await self.list_machinery_rentals(category=category, district=district, state=state)

    async def find_nearby_machinery(self, field_id: str, radius_km: float = 25, category: str | None = None) -> dict[str, Any]:
        """Find machinery around a farmer-owned field without accepting raw coordinates."""
        try:
            field = await self.client.get(f"/v1/fields/{quote(field_id, safe='')}")
            latitude, longitude = field.data.get("centroid_lat"), field.data.get("centroid_lon")
            if latitude is None or longitude is None:
                return tool_degraded(summary="Nearby machinery is unavailable because this field has no recorded coordinates.", data=[], warning="Add or select a field location before requesting nearby providers.", request_id=field.request_id)
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return await self._read("Nearby machinery listings loaded for the selected field.", self.client.get("/machinery-rentals/nearby", params={"lat": latitude, "lon": longitude, "radius_km": min(max(radius_km, 1), 250), "category": category}))

    async def search_marketplace_listings(
        self,
        listing_type: str | None = None,
        category: str | None = None,
        district: str | None = None,
        state: str | None = None,
        query: str | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        """Discover source-attributed listings; this tool cannot transact or contact providers."""
        return await self._read(
            "Marketplace directory listings loaded. These are public discovery records, not booking or purchase offers.",
            self.client.get(
                "/marketplace/listings",
                params={
                    "listing_type": listing_type,
                    "category": category,
                    "district": district,
                    "state": state,
                    "query": query,
                    "limit": min(max(limit, 1), 100),
                },
            ),
        )

    async def find_nearby_marketplace_listings(self, field_id: str, radius_km: float = 25, listing_type: str | None = None) -> dict[str, Any]:
        """Find source-attributed directory records near a farmer-owned field."""
        try:
            field = await self.client.get(f"/v1/fields/{quote(field_id, safe='')}")
            latitude, longitude = field.data.get("centroid_lat"), field.data.get("centroid_lon")
            if latitude is None or longitude is None:
                return tool_degraded(summary="Nearby marketplace listings are unavailable because this field has no recorded coordinates.", data=[], warning="Add or select a field location before requesting nearby providers.", request_id=field.request_id)
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return await self._read("Nearby marketplace listings loaded for the selected field.", self.client.get("/marketplace/nearby", params={"lat": latitude, "lon": longitude, "radius_km": min(max(radius_km, 1), 250), "listing_type": listing_type}))

    async def get_marketplace_status(self) -> dict[str, Any]:
        return await self._read(
            "Marketplace directory setup status loaded. A configured source still needs a successful ingestion before it has listings.",
            self.client.get("/marketplace/status"),
        )

    async def find_seed_suppliers(self, district: str | None = None, state: str | None = None, query: str | None = None) -> dict[str, Any]:
        return await self.search_marketplace_listings("seed", district=district, state=state, query=query)

    async def find_fertilizer_suppliers(self, district: str | None = None, state: str | None = None, query: str | None = None) -> dict[str, Any]:
        return await self.search_marketplace_listings("fertilizer", district=district, state=state, query=query)

    async def find_logistics_providers(self, district: str | None = None, state: str | None = None, query: str | None = None) -> dict[str, Any]:
        return await self.search_marketplace_listings("logistics", district=district, state=state, query=query)

    async def find_crop_buyers(self, district: str | None = None, state: str | None = None, query: str | None = None) -> dict[str, Any]:
        return await self.search_marketplace_listings("buyer", district=district, state=state, query=query)

    async def find_exporters(self, district: str | None = None, state: str | None = None, query: str | None = None) -> dict[str, Any]:
        return await self.search_marketplace_listings("exporter", district=district, state=state, query=query)

    async def compare_marketplace_quotes(self, quotes: list[dict[str, Any]]) -> dict[str, Any]:
        """Rank explicit supplier quotes; no missing costs or currency conversion are inferred."""
        return await self._read(
            "Quote comparison completed from the supplied quotes. Verify same currency and unit before choosing.",
            self.client.post(
                "/marketplace/compare-quotes",
                json={"quotes": quotes},
                idempotency_key=self._idempotency_key("/marketplace/compare-quotes", {"quotes": quotes}),
            ),
        )

    async def compare_machinery_costs(self, quotes: list[dict[str, Any]]) -> dict[str, Any]:
        return await self.compare_marketplace_quotes(quotes)

    async def compare_logistics_options(self, quotes: list[dict[str, Any]]) -> dict[str, Any]:
        return await self.compare_marketplace_quotes(quotes)

    async def calculate_logistics_cost(self, quote: dict[str, Any]) -> dict[str, Any]:
        """Calculate an all-in logistics total from one explicit quote."""
        return await self.compare_marketplace_quotes([quote])

    async def update_profile(
        self,
        name: str,
        phone: str | None = None,
        location: str | None = None,
        preferred_language: str = "en",
        latitude: float | None = None,
        longitude: float | None = None,
        notifications_enabled: bool = True,
        notification_channels: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "phone": phone,
            "location": location,
            "preferred_language": preferred_language,
            "latitude": latitude,
            "longitude": longitude,
            "notification_preferences": {
                "enabled": notifications_enabled,
                "channels": notification_channels or ["in_app"],
            },
        }
        return await self._write("Farmer profile updated.", "/v1/profile", payload, method="PUT")

    async def create_field(
        self,
        name: str,
        area_acres: float,
        boundary_geojson: dict[str, Any],
        current_crop: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "area_acres": area_acres,
            "boundary_geojson": boundary_geojson,
            "current_crop": current_crop,
        }
        return await self._write("Field created.", "/v1/fields", payload)

    async def start_crop_cycle(
        self,
        field_id: str,
        crop_name: str,
        planted_at: str,
        expected_harvest_date: str | None = None,
        initial_stage: str = "sowing",
    ) -> dict[str, Any]:
        payload = {
            "crop_name": crop_name,
            "planted_at": planted_at,
            "expected_harvest_date": expected_harvest_date,
            "initial_stage": initial_stage,
        }
        return await self._write(
            "Crop cycle started.",
            f"/v1/fields/{quote(field_id, safe='')}/crop-cycles",
            payload,
        )

    async def get_harvest_lots(self, field_id: str) -> dict[str, Any]:
        return await self._read(
            "Farmer-reported harvest lots loaded; quantities are not independently verified.",
            self.client.get(f"/v1/fields/{quote(field_id, safe='')}/harvest-lots"),
        )

    async def record_harvest(
        self,
        crop_cycle_id: str,
        harvested_on: str,
        quantity: float,
        unit: str,
        grade: str | None = None,
        storage_note: str | None = None,
        final_harvest: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "harvested_on": harvested_on,
            "quantity": quantity,
            "unit": unit,
            "grade": grade,
            "storage_note": storage_note,
            "final_harvest": final_harvest,
        }
        return await self._write(
            "Farmer-reported harvest lot recorded; no sale or payment was made.",
            f"/v1/crop-cycles/{quote(crop_cycle_id, safe='')}/harvest-lots",
            payload,
        )

    async def update_crop_stage(
        self,
        cycle_id: str,
        stage: str,
        occurred_at: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        payload = {"stage": stage, "occurred_at": occurred_at, "note": note}
        return await self._write(
            "Crop stage updated.",
            f"/v1/crop-cycles/{quote(cycle_id, safe='')}/stage",
            payload,
        )

    async def record_soil_test(
        self,
        field_id: str,
        observed_at: str,
        source: str,
        ph: float | None = None,
        organic_carbon: float | None = None,
        nitrogen: float | None = None,
        phosphorus: float | None = None,
        potassium: float | None = None,
        ec: float | None = None,
        moisture_percent: float | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        payload = {
            "observed_at": observed_at,
            "ph": ph,
            "organic_carbon": organic_carbon,
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
            "ec": ec,
            "moisture_percent": moisture_percent,
            "source": source,
            "confidence": confidence,
        }
        return await self._write(
            "Soil test recorded.",
            f"/v1/fields/{quote(field_id, safe='')}/soil-tests",
            payload,
        )

    async def update_alert_status(self, alert_id: str, status: str) -> dict[str, Any]:
        payload = {"status": status}
        return await self._write(
            "Alert status updated.",
            f"/v1/alerts/{quote(alert_id, safe='')}",
            payload,
            method="PATCH",
        )

    async def record_sensor_reading(
        self,
        field_id: str,
        measurement: str,
        value: float,
        unit: str,
        observed_at: str,
        source: str,
        device_id: str | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        payload = {
            "field_id": field_id,
            "device_id": device_id,
            "measurement": measurement,
            "value": value,
            "unit": unit,
            "observed_at": observed_at,
            "source": source,
            "confidence": confidence,
        }
        return await self._write("Sensor reading recorded.", "/v1/sensor-readings", payload)

    async def create_advisor_session(self, field_id: str | None = None, language: str = "en") -> dict[str, Any]:
        payload = {"field_id": field_id, "language": language}
        return await self._write("Advisor session created.", "/v1/advisor/sessions", payload)

    async def ask_farm_advisor(
        self,
        content: str,
        session_id: str | None = None,
        field_id: str | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        try:
            if session_id is None:
                session = await self.client.post(
                    "/v1/advisor/sessions",
                    json={"field_id": field_id, "language": language},
                    idempotency_key=self._idempotency_key(
                        "/v1/advisor/sessions", {"field_id": field_id, "language": language}
                    ),
                )
                session_id = session.data["id"]
            payload = {"content": content}
            message = await self.client.post(
                f"/v1/advisor/sessions/{quote(session_id, safe='')}/messages",
                json=payload,
                idempotency_key=self._idempotency_key(
                    f"/v1/advisor/sessions/{session_id}/messages", payload
                ),
            )
        except (BackendError, KeyError, TypeError) as exc:
            if isinstance(exc, BackendError):
                return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
            return tool_error(summary="The advisor returned an invalid session response.", code="advisor_invalid_response", retryable=False)
        return tool_result(
            status="ok",
            summary="Farm advisor response loaded. Provider availability and citations are preserved in the response.",
            data={"session_id": session_id, "message": message.data},
            request_id=message.request_id,
            max_response_bytes=self.max_response_bytes,
        )

    async def diagnose_crop(
        self,
        image_base64: str,
        mime_type: str = "image/jpeg",
        field_id: str | None = None,
        confirmed_crop: str | None = None,
    ) -> dict[str, Any]:
        allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        if mime_type not in allowed:
            return tool_error(summary="Only JPEG, PNG, and WebP crop images are accepted.", code="invalid_image_type", retryable=False)
        try:
            image = base64.b64decode(image_base64, validate=True)
        except (binascii.Error, ValueError):
            return tool_error(summary="The image_base64 value is not valid base64.", code="invalid_image_base64", retryable=False)
        if not image or len(image) > 10 * 1024 * 1024:
            return tool_error(summary="The crop image must be between 1 byte and 10 MB.", code="invalid_image_size", retryable=False)
        boundary = "----KisanSathiMcpBoundary"
        chunks = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"crop{allowed[mime_type]}\"\r\nContent-Type: {mime_type}\r\n\r\n".encode(),
            image,
        ]
        if field_id:
            chunks.append(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"field_id\"\r\n\r\n{field_id}".encode())
        if confirmed_crop:
            chunks.append(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"confirmed_crop\"\r\n\r\n{confirmed_crop}".encode())
        chunks.append(f"\r\n--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        key_payload = {"field_id": field_id, "confirmed_crop": confirmed_crop, "mime_type": mime_type, "sha256": hashlib.sha256(image).hexdigest()}
        try:
            response = await self.client.post_bytes(
                "/v1/diagnoses",
                content=body,
                content_type=f"multipart/form-data; boundary={boundary}",
                idempotency_key=self._idempotency_key("/v1/diagnoses", key_payload),
            )
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return tool_result(
            status="ok",
            summary="Crop diagnosis result loaded. Inconclusive/provider-unavailable states are preserved.",
            data=response.data,
            request_id=response.request_id,
            max_response_bytes=self.max_response_bytes,
        )

    async def assess_crop_problem(
        self,
        upload_id: str,
        consent_receipt_id: str,
        field_id: str | None = None,
        confirmed_crop: str | None = None,
    ) -> dict[str, Any]:
        """Assess host-staged photo evidence without passing image bytes to the model."""
        payload = {"upload_id": upload_id, "consent_receipt_id": consent_receipt_id, "confirmed_crop": confirmed_crop}
        try:
            response = await self.client.post(
                "/v1/diagnoses/from-upload", json=payload,
                idempotency_key=self._idempotency_key("/v1/diagnoses/from-upload", {**payload, "field_id": field_id}),
            )
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return tool_result(
            status="ok", summary="Crop-health assessment loaded. Visual candidates and sensor context remain separate screening evidence.",
            data=response.data, request_id=response.request_id, max_response_bytes=self.max_response_bytes,
        )

    async def submit_diagnosis_feedback(
        self,
        diagnosis_id: str,
        correctness: str,
        label: str | None = None,
        confirmed_crop: str | None = None,
        share_for_model_improvement: bool = False,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Save a farmer's review lead; it never exports an image or trains a model."""
        allowed = {"confirmed", "corrected", "unknown"}
        normalized_correctness = correctness.strip().lower()
        normalized_label = label.strip() if label else None
        if normalized_correctness not in allowed:
            return tool_error(summary="Correctness must be confirmed, corrected, or unknown.", code="invalid_feedback_correctness", retryable=False)
        if normalized_correctness != "unknown" and not normalized_label:
            return tool_error(summary="A condition label is required when feedback is confirmed or corrected.", code="missing_feedback_label", retryable=False)
        payload = {
            "correctness": normalized_correctness,
            "label": normalized_label,
            "confirmed_crop": confirmed_crop.strip() if confirmed_crop else None,
            "share_for_model_improvement": bool(share_for_model_improvement),
            "note": note.strip() if note else None,
        }
        return await self._write(
            "Diagnosis feedback saved as a farmer review lead. It is not automatic model training or an image export.",
            f"/v1/diagnoses/{quote(diagnosis_id, safe='')}/feedback",
            payload,
        )

    async def send_voice_turn(self, audio_base64: str, mime_type: str = "audio/webm") -> dict[str, Any]:
        try:
            audio = base64.b64decode(audio_base64, validate=True)
        except (binascii.Error, ValueError):
            return tool_error(summary="The audio_base64 value is not valid base64.", code="invalid_audio_base64", retryable=False)
        if not audio or len(audio) > 10 * 1024 * 1024:
            return tool_error(summary="The audio payload must be between 1 byte and 10 MB.", code="invalid_audio_size", retryable=False)
        try:
            response = await self.client.post_bytes("/v1/voice/turns", content=audio, content_type=mime_type)
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return tool_result(
            status="ok",
            summary="Voice turn result loaded. Provider-unavailable states are preserved.",
            data=response.data,
            request_id=response.request_id,
            max_response_bytes=self.max_response_bytes,
        )

    async def transcribe_audio(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
        language_code: str | None = None,
    ) -> dict[str, Any]:
        try:
            audio = base64.b64decode(audio_base64, validate=True)
        except (binascii.Error, ValueError):
            return tool_error(summary="The audio_base64 value is not valid base64.", code="invalid_audio_base64", retryable=False)
        if not audio or len(audio) > 10 * 1024 * 1024:
            return tool_error(summary="The audio payload must be between 1 byte and 10 MB.", code="invalid_audio_size", retryable=False)
        try:
            response = await self.client.post_bytes(
                "/v1/voice/transcribe",
                content=audio,
                content_type=mime_type,
                params={"language_code": language_code},
            )
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return tool_result(
            status="ok", summary="Speech transcription result loaded; provider-unavailable states are preserved.",
            data=response.data, request_id=response.request_id, max_response_bytes=self.max_response_bytes,
        )

    async def synthesize_speech(
        self,
        text: str,
        language_code: str,
        speaker: str | None = None,
        model: str | None = None,
        pace: float | None = None,
    ) -> dict[str, Any]:
        payload = {"text": text, "language_code": language_code, "speaker": speaker, "model": model, "pace": pace}
        try:
            response = await self.client.post(
                "/v1/voice/synthesize", json=payload,
                idempotency_key=self._idempotency_key("/v1/voice/synthesize", payload),
            )
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return tool_result(
            status="ok", summary="Sarvam speech synthesis result loaded; audio remains base64 encoded.",
            data=response.data, request_id=response.request_id, max_response_bytes=self.max_response_bytes,
        )

    async def translate_text(
        self,
        text: str,
        source_language_code: str,
        target_language_code: str,
        model: str | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "input": text,
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
            "model": model,
            "mode": mode,
        }
        try:
            response = await self.client.post(
                "/v1/translate", json=payload,
                idempotency_key=self._idempotency_key("/v1/translate", payload),
            )
        except BackendError as exc:
            return tool_error(summary=exc.message, code=exc.code, retryable=exc.retryable, request_id=exc.request_id)
        return tool_result(
            status="ok", summary="Sarvam translation result loaded; source and target language codes are preserved.",
            data=response.data, request_id=response.request_id, max_response_bytes=self.max_response_bytes,
        )

    async def calculate_profit(
        self,
        revenue: float,
        expenses: list[dict[str, Any]] | None = None,
        quantity_quintals: float | None = None,
        sale_price_per_quintal: float | None = None,
    ) -> dict[str, Any]:
        if revenue < 0 or (quantity_quintals is not None and quantity_quintals < 0) or (sale_price_per_quintal is not None and sale_price_per_quintal < 0):
            return tool_error(summary="Revenue, quantity, and sale price cannot be negative.", code="invalid_finance_input", retryable=False)
        normalized = expenses or []
        total_expenses = 0.0
        breakdown = []
        for item in normalized:
            amount = item.get("amount") if isinstance(item, dict) else None
            if not isinstance(amount, (int, float)) or amount < 0:
                return tool_error(summary="Each expense must contain a non-negative numeric amount.", code="invalid_finance_expense", retryable=False)
            total_expenses += float(amount)
            breakdown.append({"title": str(item.get("title") or "Expense"), "amount": float(amount)})
        modeled_revenue = float(revenue)
        if quantity_quintals is not None and sale_price_per_quintal is not None:
            modeled_revenue = float(quantity_quintals) * float(sale_price_per_quintal)
        return tool_result(
            status="ok",
            summary="Profit calculation completed locally from user-provided assumptions; no financial ledger was persisted.",
            data={
                "revenue": modeled_revenue,
                "expenses": total_expenses,
                "profit": modeled_revenue - total_expenses,
                "expense_breakdown": breakdown,
                "assumptions": {"quantity_quintals": quantity_quintals, "sale_price_per_quintal": sale_price_per_quintal},
            },
            source="local_calculation",
        )

    async def record_irrigation_event(
        self,
        field_id: str,
        occurred_at: str,
        volume_liters: float | None = None,
        duration_minutes: float | None = None,
        method: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "field_id": field_id,
            "occurred_at": occurred_at,
            "volume_liters": volume_liters,
            "duration_minutes": duration_minutes,
            "method": method,
            "note": note,
        }
        return await self._write(
            "Irrigation event recorded. No pump or valve was controlled.",
            "/v1/irrigation-events",
            payload,
        )

    async def create_reminder(
        self,
        reminder_type: str,
        scheduled_for: str,
        title: str,
        field_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "field_id": field_id,
            "reminder_type": reminder_type,
            "scheduled_for": scheduled_for,
            "title": title,
        }
        return await self._write("Reminder created.", "/v1/reminders", payload)

    async def create_report(
        self,
        report_type: str = "farm_summary",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        payload = {"report_type": report_type, "from_date": from_date, "to_date": to_date}
        return await self._write("Farm report created.", "/v1/reports", payload)
