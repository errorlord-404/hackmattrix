from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .backend_client import BackendClient
from .tools import KisanSathiTools


_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_EXTERNAL_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def build_server(client: BackendClient) -> FastMCP:
    server = FastMCP(
        name="kisansathi",
        instructions=(
            "KisanSathi provides farmer-scoped read tools backed by the farm API. "
            "Use tool results as the source of truth. Preserve source, freshness, "
            "assumptions, and uncertainty. Never invent missing farm observations. "
            "The farmer identity is fixed by the launcher and is not a tool argument."
        ),
    )
    tools = KisanSathiTools(client)

    def register(
        name: str,
        description: str,
        function: Callable[..., Any],
        annotations: ToolAnnotations = _READ_ONLY,
    ) -> None:
        server.tool(name=name, description=description, annotations=annotations)(function)

    register("get_farm_overview", "Load the current farmer-scoped dashboard, fields, open alerts, and data warnings.", tools.get_farm_overview)
    register("get_component_health", "Load safe farm-service, reference-catalog, provider, and demo-data health without exposing paths or credentials.", tools.get_component_health)
    register("get_onboarding_status", "Identify missing profile, location, fields, boundary review, crop, sensor evidence, and optional provider readiness for the bound farmer without creating records.", tools.get_onboarding_status)
    register("get_diagnosis", "Load one farmer-scoped crop-photo evidence record by ID, including provider availability, crop/model candidates, and limitations. A candidate is not a confirmed disease.", tools.get_diagnosis)
    register("get_profile", "Load the current farmer profile and preferred language/location settings.", tools.get_profile)
    register("list_fields", "List the farmer's active fields, optionally including inactive fields.", tools.list_fields)
    register("get_farm_map", "Load field boundaries and current map metrics for the farmer's active fields.", tools.get_farm_map)
    register("get_field", "Load one farmer-scoped field by its exact field ID.", tools.get_field)
    register("update_field", "Update a farmer field after explicit confirmation.", tools.update_field, _WRITE)
    register("get_field_timeline", "Load crop-cycle and stage history for one field.", tools.get_field_timeline)
    register("get_harvest_lots", "Load farmer-reported harvested quantity, unit, grade, and lot identity for one field; no yield is inferred.", tools.get_harvest_lots)
    register("get_crop_stage_action_proposals", "Load stage-aware suggested tasks for a field. They never create a task or execute work without farmer confirmation.", tools.get_crop_stage_action_proposals)
    register("get_soil_health", "Load the latest soil test, observations, screening status, recommendations, and provenance for a field.", tools.get_soil_health)
    register("get_crop_options", "Compare sourced crop catalog options using farmer-confirmed season, prior crop, and soil type. It is not a yield or profit prediction.", tools.get_crop_options)
    register("get_latest_field_observations", "Load the latest sensor observations grouped by measurement for a field.", tools.get_latest_field_observations)
    register("get_tomato_demo", "Load the Tomato prototype simulator status and source-labelled observations for a field. It is read-only and never controls hardware.", tools.get_tomato_demo)
    register("list_device_health", "Load field device freshness and telemetry status. It cannot provision devices or control equipment.", tools.list_device_health)
    register("get_weather_for_field", "Load weather for a field using coordinates stored on that field; never provide coordinates from memory.", tools.get_weather_for_field)
    register("get_weather_alerts_for_field", "Load weather alerts for a field, including forecast provenance.", tools.get_weather_alerts_for_field)
    register("get_irrigation_advice", "Load deterministic irrigation screening advice; this never activates equipment.", tools.get_irrigation_advice)
    register("list_irrigation_events", "Load farmer-recorded irrigation history. It does not infer water volume or control equipment.", tools.list_irrigation_events)
    register("list_alerts", "List farmer-scoped alerts, optionally filtered by status.", tools.list_alerts)
    register("list_reminders", "List farmer-scoped scheduled reminders.", tools.list_reminders)
    register("list_field_tasks", "List farmer-confirmed field tasks, optionally scoped to a field and status.", tools.list_field_tasks)
    register("list_ledger_entries", "List farmer-entered INR ledger records. This cannot execute payments, transfers, or credit actions.", tools.list_ledger_entries)
    register("get_ledger_summary", "Load the active farmer-entered INR income, expense, and balance summary; it is not a forecast or credit decision.", tools.get_ledger_summary)
    register("list_reports", "List farmer-scoped generated reports.", tools.list_reports)
    register("get_report", "Load one farmer-scoped report by its exact report ID.", tools.get_report)
    register("get_market_summary", "Load latest market prices with source and freshness metadata.", tools.get_market_summary)
    register("get_market_price", "Load latest market prices for a crop, optionally scoped to district and state.", tools.get_market_price)
    register("get_nearby_mandi_prices", "Load latest comparable mandi prices scoped to a farmer-supplied district and state.", tools.get_nearby_mandi_prices)
    register("get_market_trend", "Load a bounded market-price trend for a crop and optional mandi.", tools.get_market_trend)
    register("get_market_history", "Load bounded historical market prices for a crop and optional mandi.", tools.get_market_history)
    register("compare_mandis", "Compare net mandi realisation using explicit farmer location and quantity assumptions.", tools.compare_mandis)
    register("compare_sale_routes", "Rank sale routes only when the farmer supplies exact market-price record IDs, dated road distance and cost quotes; stale or incomparable data yields no recommendation. Read-only calculation; it cannot book transport or sell produce.", tools.compare_sale_routes)
    register("get_msp", "Load minimum support price records for a crop.", tools.get_msp)
    register("compare_msp_with_market", "Compare official MSP records with the newest sourced price per mandi. It does not guarantee procurement.", tools.compare_msp_with_market)
    register("find_government_schemes", "Load government schemes applicable to a state.", tools.find_government_schemes)
    register("list_government_schemes", "Load the government scheme reference catalog.", tools.list_government_schemes)
    register("list_crops", "Load the crop reference catalog used by the frontend.", tools.list_crops)
    register("get_crop", "Load one crop reference record by its exact ID.", tools.get_crop)
    register("recommend_seeds", "Load seed recommendations from the reference backend; do not invent varieties.", tools.recommend_seeds)
    register("recommend_fertilizers", "Load fertilizer recommendations from the reference backend; do not invent products.", tools.recommend_fertilizers)
    register("check_scheme_eligibility", "Check government-scheme eligibility using explicit state and criteria inputs.", tools.check_scheme_eligibility)
    register("get_scheme_details", "Load one government scheme reference record by its exact ID.", tools.get_scheme_details)
    register("query_support_catalog", "Answer one farmer support prompt with bounded, source-attributed government schemes, machinery rentals, and marketplace directory records. This is read-only discovery; it never books, buys, sells, or guarantees eligibility, stock, price, or availability.", tools.query_support_catalog)
    register("list_machinery_rentals", "Load machinery rental listings with optional category and location filters.", tools.list_machinery_rentals)
    register("find_machinery", "Find nearby machinery-rental records with optional category and location filters.", tools.find_machinery)
    register("find_nearby_machinery", "Find source-attributed machinery near a farmer-owned field. The field coordinates are read from backend state and cannot be supplied by the model.", tools.find_nearby_machinery)
    register("search_marketplace_listings", "Search source-attributed machinery, input, logistics, buyer, and exporter directory records. This only discovers contacts; it cannot transact.", tools.search_marketplace_listings)
    register("find_nearby_marketplace_listings", "Find source-attributed directory records near a farmer-owned field. This only discovers contacts; it cannot transact.", tools.find_nearby_marketplace_listings)
    register("get_marketplace_status", "Report whether approved public directory sources are configured; it never claims stock or provider availability.", tools.get_marketplace_status)
    register("find_seed_suppliers", "Find source-attributed seed suppliers. Listings are discovery-only and never guarantee stock or price.", tools.find_seed_suppliers)
    register("find_fertilizer_suppliers", "Find source-attributed fertilizer suppliers. Listings are discovery-only and never guarantee stock or price.", tools.find_fertilizer_suppliers)
    register("find_logistics_providers", "Find source-attributed logistics providers. This does not book transport or estimate an unpublished quote.", tools.find_logistics_providers)
    register("find_crop_buyers", "Find source-attributed crop buyers. This does not submit a sale or guarantee buyer acceptance.", tools.find_crop_buyers)
    register("find_exporters", "Find source-attributed exporters. This does not determine export eligibility or submit export paperwork.", tools.find_exporters)
    register("compare_marketplace_quotes", "Rank explicit supplier quotes by disclosed cost components. It never estimates hidden costs or converts currencies.", tools.compare_marketplace_quotes)
    register("compare_machinery_costs", "Compare farmer-provided machinery quotes by their disclosed all-in costs.", tools.compare_machinery_costs)
    register("compare_logistics_options", "Compare farmer-provided logistics quotes by their disclosed all-in costs.", tools.compare_logistics_options)
    register("calculate_logistics_cost", "Calculate an all-in logistics cost from one supplier-provided quote.", tools.calculate_logistics_cost)
    register("record_irrigation_event", "Record a farmer-confirmed irrigation event. This only records history and never controls equipment.", tools.record_irrigation_event, _WRITE)
    register("create_reminder", "Create a farmer-confirmed reminder for a field or the whole farm.", tools.create_reminder, _WRITE)
    register("create_field_task", "Create a farmer-confirmed actionable task for a field; it does not order inputs or control equipment.", tools.create_field_task, _WRITE)
    register("update_field_task_status", "Complete or cancel a farmer-confirmed field task.", tools.update_field_task_status, _WRITE)
    register("record_ledger_entry", "Record a farmer-confirmed INR income or expense. This is record-keeping only and never moves money.", tools.record_ledger_entry, _WRITE)
    register("update_ledger_entry_status", "Void or reactivate a farmer-confirmed ledger record while retaining its audit history.", tools.update_ledger_entry_status, _WRITE)
    register("create_report", "Create a farmer-confirmed farm report snapshot.", tools.create_report, _WRITE)
    register("update_profile", "Update farmer profile fields after explicit confirmation.", tools.update_profile, _WRITE)
    register("create_field", "Create a farmer field from a confirmed name, area, and GeoJSON boundary.", tools.create_field, _WRITE)
    register("start_crop_cycle", "Start a crop cycle on a confirmed field.", tools.start_crop_cycle, _WRITE)
    register("record_harvest", "Record one farmer-confirmed harvest lot on an active crop cycle. Final harvest closes the cycle; this does not sell produce or move money.", tools.record_harvest, _WRITE)
    register("update_crop_stage", "Record a confirmed crop-stage update.", tools.update_crop_stage, _WRITE)
    register("record_soil_test", "Record a confirmed soil test with its source and observation time.", tools.record_soil_test, _WRITE)
    register("update_alert_status", "Acknowledge or dismiss a farmer-scoped alert after confirmation.", tools.update_alert_status, _WRITE)
    register("record_sensor_reading", "Record a confirmed field sensor reading; this does not control hardware.", tools.record_sensor_reading, _WRITE)
    register("create_advisor_session", "Create a farmer-scoped advisor session after confirmation.", tools.create_advisor_session, _WRITE)
    register("ask_farm_advisor", "Send a farmer question to the configured advisor provider and preserve unavailable states.", tools.ask_farm_advisor, _WRITE)
    register("diagnose_crop", "Submit a crop image with farmer-confirmed crop when known; preserve review/provider-unavailable states.", tools.diagnose_crop, _WRITE)
    register("assess_crop_problem", "Submit a farmer-approved, privately staged crop photo to the configured external crop-health provider and return visual candidates with immutable sensor context. It never prescribes chemical or fertilizer doses.", tools.assess_crop_problem, _EXTERNAL_WRITE)
    register("submit_diagnosis_feedback", "Save farmer-confirmed feedback for one diagnosis. It is a review lead only: no automatic training, image export, or diagnosis confirmation occurs.", tools.submit_diagnosis_feedback, _WRITE)
    register("send_voice_turn", "Send recorded audio to the configured voice provider and preserve unavailable states.", tools.send_voice_turn, _WRITE)
    register("transcribe_audio", "Transcribe farmer audio through the configured speech-to-text provider.", tools.transcribe_audio, _WRITE)
    register("synthesize_speech", "Synthesize speech through the configured text-to-speech provider.", tools.synthesize_speech, _WRITE)
    register("translate_text", "Translate farmer text through the configured language provider.", tools.translate_text, _WRITE)
    register("calculate_profit", "Calculate profit from explicit user-provided assumptions without persisting financial data.", tools.calculate_profit)
    return server
