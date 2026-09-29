from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from api_client import ActorScope, ApiClient, ExecutionContext, idempotency_key  # noqa: E402
from errors import PolicyError  # noqa: E402
from executor import ToolExecutor  # noqa: E402
from policy import DEFAULT_POLICY  # noqa: E402


def context() -> ExecutionContext:
    actor = ActorScope(sub="user-1", tenant_id="tenant-1", farmer_id="farmer-1", roles=("farmer",), session_id="session-1")
    return ExecutionContext(actor=actor, request_id="request-1", session_id="session-1", turn_id="turn-1", tool_call_id="call-1")


def test_workflow_selects_minimal_allowlist_and_capability_filters() -> None:
    assert len(DEFAULT_POLICY.select_tools("farm_context")) == 9
    assert len(DEFAULT_POLICY.select_tools("farm_context")) < 78
    assert all(tool.name != "diagnose_crop" for tool in DEFAULT_POLICY.select_tools("crop_health", provider_capabilities={"text_input"}))
    assert any(tool.name == "diagnose_crop" for tool in DEFAULT_POLICY.select_tools("crop_health", provider_capabilities={"text_input", "image_input"}))


def test_policy_rejects_unknown_out_of_workflow_and_injected_arguments() -> None:
    with pytest.raises(PolicyError, match="outside"):
        DEFAULT_POLICY.authorize("farm_context", "create_field", {})
    with pytest.raises(PolicyError, match="not registered"):
        DEFAULT_POLICY.authorize("farm_context", "control_pump", {})
    with pytest.raises(PolicyError, match="Identity"):
        DEFAULT_POLICY.authorize("farm_context", "list_fields", {"tenant_id": "attacker"})
    with pytest.raises(PolicyError, match="Identity"):
        DEFAULT_POLICY.authorize("support_market", "query_support_catalog", {"source": {"authorization": "Bearer secret"}})


def test_persistent_effects_require_confirmation_but_compute_does_not() -> None:
    assert DEFAULT_POLICY.requires_confirmation("record_update", "create_field") is True
    assert DEFAULT_POLICY.requires_confirmation("crop_health", "diagnose_crop") is False
    assert DEFAULT_POLICY.classify("calculate_profit") == "external_compute"


@pytest.mark.asyncio
async def test_executor_injects_actor_headers_and_derives_write_idempotency() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "field-1", "name": "North"}, headers={"X-Request-ID": "backend-1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://api.example.test") as raw:
        client = ApiClient("https://api.example.test", actor_context_secret="test-signing-secret", client=raw)
        result = await ToolExecutor(client).execute(
            "create_field",
            {"name": "North", "area_acres": 2},
            context(),
            workflow="record_update",
            approval=True,
        )

    assert result["status"] == "ok"
    assert result["data"] == {"id": "field-1", "name": "North"}
    assert result["action"]["method"] == "POST"
    assert len(seen) == 1
    request = seen[0]
    assert request.url.path == "/v1/fields"
    assert request.headers["X-Request-ID"] == "request-1"
    assert request.headers["X-Internal-Actor-Context"]
    assert request.headers["Idempotency-Key"] == idempotency_key(context().actor, "create_field", "/v1/fields", {"name": "North", "area_acres": 2})
    assert "tenant_id" not in request.content.decode("utf-8")
    assert "farmer_id" not in request.content.decode("utf-8")


@pytest.mark.asyncio
async def test_write_without_confirmation_has_no_backend_effect() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.example.test") as raw:
        client = ApiClient("https://api.example.test", client=raw)
        result = await ToolExecutor(client).execute("create_field", {"name": "North"}, context(), workflow="record_update")
    assert result["status"] == "needs_approval"
    assert called is False


@pytest.mark.asyncio
async def test_backend_error_is_bounded_and_does_not_expose_secret_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"detail": {"code": "provider_failed", "message": "authorization=Bearer super-secret"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.example.test") as raw:
        client = ApiClient("https://api.example.test", client=raw)
        result = await ToolExecutor(client).execute("list_fields", {}, context(), workflow="farm_context")
    assert result["status"] == "error"
    assert result["data"]["code"] == "provider_failed"
    assert "super-secret" not in str(result)
