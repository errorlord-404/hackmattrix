from __future__ import annotations

import asyncio
import base64
import inspect
import json

import httpx

from kisansathi_agent.backend_client import BackendClient
from kisansathi_agent.config import Settings
from kisansathi_agent.server import build_server
from kisansathi_agent.tools import KisanSathiTools
from kisansathi_agent.result import bound_data


def test_agent_env_supplies_local_demo_defaults_without_overriding_launcher(monkeypatch) -> None:
    monkeypatch.delenv("KISANSATHI_BACKEND_URL", raising=False)
    monkeypatch.delenv("KISANSATHI_FARMER_ID", raising=False)
    settings = Settings.from_env()
    assert settings.backend_url == "http://127.0.0.1:8001"
    assert settings.farmer_id == "demo"
    monkeypatch.setenv("KISANSATHI_BACKEND_URL", "http://launcher.test")
    monkeypatch.setenv("KISANSATHI_FARMER_ID", "launcher-farmer")
    overridden = Settings.from_env()
    assert overridden.backend_url == "http://launcher.test"
    assert overridden.farmer_id == "launcher-farmer"


def run(coro):
    return asyncio.run(coro)


def make_client(handler):
    return BackendClient(
        Settings(backend_url="http://backend.test", farmer_id="farmer-1"),
        transport=httpx.MockTransport(handler),
    )


def test_weather_uses_coordinates_from_the_selected_field() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/v1/fields/field-1":
            return httpx.Response(200, json={"id": "field-1", "centroid_lat": 20.1, "centroid_lon": 78.2})
        if request.url.path == "/v1/weather":
            assert request.url.params["lat"] == "20.1"
            assert request.url.params["lon"] == "78.2"
            return httpx.Response(200, json={"provider": "test", "freshness_seconds": 4})
        return httpx.Response(404, json={"detail": "not found"})

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).get_weather_for_field("field-1")
        assert result["status"] == "ok"
        assert result["data"]["weather"]["provider"] == "test"
        assert [request.url.path for request in calls] == ["/v1/fields/field-1", "/v1/weather"]
        await client.aclose()

    run(scenario())


def test_tomato_demo_tool_preserves_simulation_provenance() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/fields/field-1/tomato-demo"
        assert request.headers["X-Farmer-ID"] == "farmer-1"
        return httpx.Response(200, json={
            "enabled": True,
            "field_id": "field-1",
            "running": True,
            "scenario": "water-stress",
            "source": "simulation:tomato-demo:v1",
            "observations": [{"measurement": "moisture", "value": 27.5, "unit": "%", "source": "simulation:tomato-demo:v1"}],
        })

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).get_tomato_demo("field-1")
        assert result["status"] == "ok"
        assert result["data"]["scenario"] == "water-stress"
        assert result["data"]["source"] == "simulation:tomato-demo:v1"
        await client.aclose()

    run(scenario())


def test_weather_without_coordinates_is_explicitly_degraded() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": request.url.path.rsplit("/", 1)[-1], "centroid_lat": None, "centroid_lon": None})

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).get_weather_for_field("field-1")
        assert result["status"] == "degraded"
        assert result["warnings"]
        await client.aclose()

    run(scenario())


def test_server_exposes_only_farmer_safe_read_tools() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = make_client(handler)
    server = build_server(client)
    registered = server._tool_manager.list_tools()
    names = {tool.name for tool in registered}
    public_tool_methods = {
        name for name, method in inspect.getmembers(KisanSathiTools, inspect.iscoroutinefunction)
        if not name.startswith("_")
    }
    # A capability that exists only as a Python method is not a farmer-facing
    # capability. Keep the Codex registry complete as the lifecycle grows.
    assert public_tool_methods <= names
    assert "get_profile" in names
    assert "get_component_health" in names
    assert "get_onboarding_status" in names
    assert "get_diagnosis" in names
    assert "get_harvest_lots" in names
    assert "record_harvest" in names
    assert "get_weather_for_field" in names
    assert "get_crop_stage_action_proposals" in names
    assert "get_crop_options" in names
    assert "list_device_health" in names
    assert "get_market_price" in names
    assert "compare_sale_routes" in names
    assert "compare_msp_with_market" in names
    assert "find_machinery" in names
    assert "query_support_catalog" in names
    assert "get_marketplace_status" in names
    assert "calculate_logistics_cost" in names
    assert "list_field_tasks" in names
    assert "create_field_task" in names
    assert "get_ledger_summary" in names
    assert "record_ledger_entry" in names
    assert "record_irrigation_event" in names
    assert "list_irrigation_events" in names
    assert "update_profile" in names
    assert "farmer_id" not in json.dumps([tool.model_dump() for tool in registered], default=str)
    write_tool = next(tool for tool in registered if tool.name == "record_irrigation_event")
    assert write_tool.annotations.readOnlyHint is False
    assert write_tool.annotations.idempotentHint is True
    task_write_tool = next(tool for tool in registered if tool.name == "create_field_task")
    assert task_write_tool.annotations.readOnlyHint is False
    harvest_write_tool = next(tool for tool in registered if tool.name == "record_harvest")
    assert harvest_write_tool.annotations.readOnlyHint is False
    assert harvest_write_tool.annotations.idempotentHint is True
    run(client.aclose())


def test_onboarding_tool_reads_only_bound_farmer_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/onboarding-status"
        assert request.headers["X-Farmer-ID"] == "farmer-1"
        return httpx.Response(200, json={"next_setup_step": "create_field", "fields": {"active_count": 0}})

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).get_onboarding_status()
        assert result["status"] == "ok"
        assert result["data"]["next_setup_step"] == "create_field"
        assert "action" not in result
        await client.aclose()

    run(scenario())


def test_diagnosis_tool_reads_only_bound_farmer_evidence() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/diagnoses/record-1"
        assert request.headers["X-Farmer-ID"] == "farmer-1"
        return httpx.Response(200, json={"id": "record-1", "status": "provider_unavailable", "label": None})

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).get_diagnosis("record-1")
        assert result["status"] == "ok"
        assert result["data"]["status"] == "provider_unavailable"
        assert "action" not in result
        await client.aclose()

    run(scenario())


def test_harvest_tools_use_bound_farmer_and_deterministic_idempotency() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["X-Farmer-ID"] == "farmer-1"
        if request.method == "GET":
            assert request.url.path == "/v1/fields/field-1/harvest-lots"
            return httpx.Response(200, json=[])
        assert request.method == "POST"
        assert request.url.path == "/v1/crop-cycles/cycle-1/harvest-lots"
        assert request.headers.get("Idempotency-Key", "").startswith("ks-")
        return httpx.Response(201, json={"id": "lot-1", "quantity": 25, "unit": "kg"})

    async def scenario() -> None:
        client = make_client(handler)
        tools = KisanSathiTools(client)
        assert (await tools.get_harvest_lots("field-1"))["status"] == "ok"
        first = await tools.record_harvest("cycle-1", "2026-09-20", 25, "kg")
        second = await tools.record_harvest("cycle-1", "2026-09-20", 25, "kg")
        assert first["status"] == second["status"] == "ok"
        assert calls[1].headers["Idempotency-Key"] == calls[2].headers["Idempotency-Key"]
        assert "farmer_id" not in json.dumps(first)
        await client.aclose()

    run(scenario())


def test_prompt_support_query_fans_out_to_source_catalogs_and_bounds_results() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/gov-schemes/by-state/Maharashtra":
            return httpx.Response(200, json=[
                {"name": "Farm Mechanization", "description": "tractor support", "source": "MahaDBT"},
                {"name": "Other Scheme", "description": "not related", "source": "MahaDBT"},
            ])
        if request.url.path == "/machinery-rentals":
            return httpx.Response(200, json=[{"provider_name": "CHC Pune", "category": "tractor", "source": "FARMS"}] * 20)
        if request.url.path == "/marketplace/listings":
            assert request.url.params["state"] == "Maharashtra"
            assert request.url.params["category"] == "tractor"
            return httpx.Response(200, json=[{"title": "Tractor listing", "source": "FARMS"}] * 20)
        return httpx.Response(404, json={"detail": "not found"})

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).query_support_catalog(
            state="Maharashtra",
            category="tractor",
            query="tractor",
            limit=2,
        )
        assert result["status"] == "ok"
        assert result["data"]["filters"]["limit"] == 2
        assert len(result["data"]["results"]["schemes"]) == 1
        assert len(result["data"]["results"]["machinery"]) == 2
        assert len(result["data"]["results"]["marketplace"]) == 2
        assert {request.url.path for request in calls} == {
            "/gov-schemes/by-state/Maharashtra",
            "/machinery-rentals",
            "/marketplace/listings",
        }
        await client.aclose()

    run(scenario())


def test_mutation_sends_deterministic_idempotency_key() -> None:
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"id": "event-1"})

    async def scenario() -> None:
        client = make_client(handler)
        tools = KisanSathiTools(client)
        first = await tools.record_irrigation_event("field-1", "2026-08-18T06:00:00Z", volume_liters=20)
        second = await tools.record_irrigation_event("field-1", "2026-08-18T06:00:00Z", volume_liters=20)
        assert first["status"] == "ok"
        assert second["status"] == "ok"
        assert first["action"]["resource_type"] == "irrigation_event"
        assert first["action"]["affected_ids"] == {"id": "event-1"}
        assert first["action"]["refresh"] == ["irrigation", "timeline", "dashboard"]
        assert first["action"]["timestamp"].endswith("+00:00")
        assert seen[0].headers["idempotency-key"] == seen[1].headers["idempotency-key"]
        await client.aclose()

    run(scenario())


def test_mutation_methods_use_the_backend_http_verb() -> None:
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        return httpx.Response(200, json={"ok": True})

    async def scenario() -> None:
        client = make_client(handler)
        tools = KisanSathiTools(client)
        await tools.update_profile("Asha")
        await tools.update_alert_status("alert-1", "read")
        await tools.create_field_task("field-1", "Inspect leaves")
        await tools.update_field_task_status("task-1", "completed")
        await tools.record_ledger_entry("expense", "Seed", "Tomato seed", 820, "2026-09-07")
        await tools.update_ledger_entry_status("ledger-1", "void")
        await tools.submit_diagnosis_feedback("diagnosis-1", "unknown", note="Need extension review")
        assert seen == ["PUT", "PATCH", "POST", "PATCH", "POST", "PATCH", "POST"]
        await client.aclose()

    run(scenario())


def test_large_list_results_are_bounded_for_model_context() -> None:
    bounded = bound_data([{"id": index, "value": "x" * 100} for index in range(500)], 1_024)
    assert bounded["truncated"] is True
    assert bounded["total_items"] == 500
    assert len(bounded["items"]) < 500


def test_specialized_tools_use_reference_and_farm_routes() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.url.params))
        if request.url.path == "/v1/fields/field-1":
            return httpx.Response(200, json={"id": "field-1", "centroid_lat": 18.5204, "centroid_lon": 73.8567})
        if request.url.path == "/v1/advisor/sessions":
            return httpx.Response(201, json={"id": "session-1"})
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"id": "message-1", "content": "provider unavailable"})
        return httpx.Response(200, json={"ok": True})

    async def scenario() -> None:
        client = make_client(handler)
        tools = KisanSathiTools(client)
        assert (await tools.get_farm_map())["status"] == "ok"
        assert (await tools.get_crop_stage_action_proposals("field-1"))["status"] == "ok"
        assert (await tools.list_device_health("field-1"))["status"] == "ok"
        assert (await tools.list_crops())["status"] == "ok"
        assert (await tools.recommend_seeds("wheat"))["status"] == "ok"
        assert (await tools.recommend_fertilizers("wheat"))["status"] == "ok"
        assert (await tools.list_machinery_rentals(state="Maharashtra"))["status"] == "ok"
        assert (await tools.find_machinery(state="Maharashtra"))["status"] == "ok"
        assert (await tools.find_nearby_machinery("field-1"))["status"] == "ok"
        assert (await tools.get_market_price("Wheat", state="Maharashtra"))["status"] == "ok"
        assert (await tools.get_nearby_mandi_prices("Wheat", "Pune", "Maharashtra"))["status"] == "ok"
        assert (await tools.compare_msp_with_market("Wheat"))["status"] == "ok"
        assert (await tools.get_scheme_details("scheme-1"))["status"] == "ok"
        marketplace = await tools.search_marketplace_listings("logistics", state="Maharashtra", query="cold storage")
        assert marketplace["status"] == "ok"
        assert (await tools.find_nearby_marketplace_listings("field-1"))["status"] == "ok"
        assert (await tools.get_marketplace_status())["status"] == "ok"
        assert (await tools.find_logistics_providers(state="Maharashtra"))["status"] == "ok"
        assert (await tools.compare_logistics_options([{"provider_name": "Carrier A", "title": "Pune run", "base_cost": 1000}]))["status"] == "ok"
        assert (await tools.calculate_logistics_cost({"provider_name": "Carrier A", "title": "Pune run", "base_cost": 1000}))["status"] == "ok"
        assert (await tools.ask_farm_advisor("What should I check?"))["status"] == "ok"
        assert (await tools.calculate_profit(1000, [{"title": "Seed", "amount": 200}]))["data"]["profit"] == 800
        assert any(method == "GET" and path == "/v1/fields/map" for method, path, _ in calls)
        assert any(method == "GET" and path == "/v1/fields/field-1/action-proposals" for method, path, _ in calls)
        assert any(method == "GET" and path == "/v1/device-ingestion/devices" for method, path, _ in calls)
        assert any(method == "GET" and path == "/crops" for method, path, _ in calls)
        assert any(path == "/seeds/recommend" for _, path, _ in calls)
        assert any(path == "/fertilizer/recommend" for _, path, _ in calls)
        assert any(path == "/marketplace/listings" for _, path, _ in calls)
        assert any(path == "/machinery-rentals/nearby" for _, path, _ in calls)
        assert any(path == "/marketplace/nearby" for _, path, _ in calls)
        assert any(path == "/marketplace/status" for _, path, _ in calls)
        assert any(path == "/marketplace/compare-quotes" for _, path, _ in calls)
        assert any(path == "/msp/compare-market" for _, path, _ in calls)
        assert any(path == "/gov-schemes/scheme-1" for _, path, _ in calls)
        await client.aclose()

    run(scenario())


def test_diagnosis_feedback_is_farmer_scoped_idempotent_and_never_a_training_action() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "POST"
        assert request.url.path == "/v1/diagnoses/diagnosis-1/feedback"
        assert request.headers["X-Farmer-ID"] == "farmer-1"
        payload = json.loads(request.content)
        assert payload == {
            "correctness": "corrected", "label": "late blight", "confirmed_crop": "tomato",
            "share_for_model_improvement": True, "note": "Leaves curl after rain",
        }
        return httpx.Response(201, json={"id": "feedback-1", "training_eligibility": "requires_expert_review_and_separate_export"})

    async def scenario() -> None:
        client = make_client(handler)
        tools = KisanSathiTools(client)
        first = await tools.submit_diagnosis_feedback(
            "diagnosis-1", "corrected", label="late blight", confirmed_crop="tomato",
            share_for_model_improvement=True, note="Leaves curl after rain",
        )
        second = await tools.submit_diagnosis_feedback(
            "diagnosis-1", "corrected", label="late blight", confirmed_crop="tomato",
            share_for_model_improvement=True, note="Leaves curl after rain",
        )
        assert first["status"] == second["status"] == "ok"
        assert first["action"]["method"] == "POST"
        assert calls[0].headers["Idempotency-Key"] == calls[1].headers["Idempotency-Key"]
        invalid = await tools.submit_diagnosis_feedback("diagnosis-1", "confirmed")
        assert invalid["status"] == "error"
        assert invalid["data"]["code"] == "missing_feedback_label"
        await client.aclose()

    run(scenario())


def test_sale_route_tool_forwards_explicit_quotes_without_inventing_costs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/market-prices/compare-routes"
        assert request.headers["X-Farmer-ID"] == "farmer-1"
        body = json.loads(request.content)
        assert body["routes"] == [{"market_price_id": "price-1", "transport_cost_inr": 1500}]
        assert "road_distance_km" not in body["routes"][0]
        return httpx.Response(200, json={"status": "not_rankable", "results": [], "warnings": ["missing distance"]})

    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).compare_sale_routes("Onion", 10, [{"market_price_id": "price-1", "transport_cost_inr": 1500}])
        assert result["status"] == "ok"
        assert result["data"]["status"] == "not_rankable"
        assert "action" not in result
        await client.aclose()

    run(scenario())


def test_binary_tools_validate_and_forward_bounded_payloads() -> None:
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"status": "provider_unavailable", "message": "not configured"})

    async def scenario() -> None:
        client = make_client(handler)
        tools = KisanSathiTools(client)
        png = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode()
        diagnosis = await tools.diagnose_crop(png, mime_type="image/png", field_id="field-1")
        voice = await tools.send_voice_turn(base64.b64encode(b"audio").decode())
        assert diagnosis["status"] == voice["status"] == "ok"
        assert seen[0].headers["content-type"].startswith("multipart/form-data;")
        assert seen[1].headers["content-type"] == "audio/webm"
        assert (await tools.diagnose_crop("not-base64"))["status"] == "error"
        await client.aclose()

    run(scenario())
