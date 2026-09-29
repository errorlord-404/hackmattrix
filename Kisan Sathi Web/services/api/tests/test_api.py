from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters.base import LLMChunk
from app.main import create_app
from app.registry.loader import RegistryError, ToolRegistry
from app.settings import ServiceSettings


class FakeAdapter:
    provider_name = "test-provider"

    def __init__(self, *, configured: bool = True, chunks: tuple[str, ...] = ("namaste", " farmer")) -> None:
        self.configured = configured
        self.chunks = chunks
        self.seen_tools: list[Mapping[str, Any]] = []
        self.closed = False

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        tools: Sequence[Mapping[str, Any]],
    ) -> AsyncIterator[LLMChunk]:
        self.seen_tools = list(tools)
        for text in self.chunks:
            await asyncio.sleep(0)
            yield LLMChunk(text=text)

    async def aclose(self) -> None:
        self.closed = True


def _events(response_text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in response_text.splitlines() if line]


def test_healthz_is_live_and_readyz_is_explicitly_degraded_when_provider_is_missing(settings: ServiceSettings) -> None:
    client = TestClient(create_app(settings))

    health = client.get("/healthz")
    ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "kisansathi-api",
        "provider": "unavailable",
    }
    assert ready.status_code == 503
    assert ready.json()["status"] == "degraded"
    assert ready.json()["provider"] == "unavailable"


def test_web_routes_require_bearer_unless_dev_mode_is_explicit(settings: ServiceSettings, contract_path: Path) -> None:
    protected = ServiceSettings(tool_contract_path=contract_path, dev_mode=False)
    client = TestClient(create_app(protected))
    assert client.get("/tools").status_code == 401
    assert client.get("/tools", headers={"Authorization": "Bearer any"}).status_code == 503

    production = ServiceSettings(
        environment="production",
        dev_mode=True,
        bearer_token="server-only-token",
        tool_contract_path=contract_path,
    )
    client = TestClient(create_app(production))
    assert client.get("/tools").status_code == 401
    assert client.get("/tools", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get(
        "/tools", headers={"Authorization": "Bearer server-only-token"}
    ).status_code == 200


def test_tools_are_loaded_from_standalone_contract(settings: ServiceSettings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/tools")

    assert response.status_code == 200
    document = response.json()
    assert document["count"] == 78
    assert document["count"] == len(document["tools"])
    assert {tool["name"] for tool in document["tools"]}.__len__() == 78
    assert all("input_schema" in tool for tool in document["tools"])


def test_unconfigured_chat_returns_typed_degraded_events(settings: ServiceSettings) -> None:
    client = TestClient(create_app(settings))
    response = client.post(
        "/chat/stream",
        json={"messages": [{"role": "user", "content": "How is my crop?"}]},
    )

    assert response.status_code == 200
    events = _events(response.text)
    assert [event["kind"] for event in events] == ["ready", "unavailable", "turnCompleted"]
    assert events[1]["payload"]["status"] == "degraded"
    assert events[1]["payload"]["code"] == "provider_unavailable"
    assert events[1]["payload"]["result"]["status"] == "degraded"
    assert "api_key" not in response.text.lower()


def test_settings_repr_does_not_contain_credentials() -> None:
    settings = ServiceSettings(
        bearer_token="web-secret",
        llm_api_key="provider-secret",
    )
    rendered = repr(settings)
    assert "web-secret" not in rendered
    assert "provider-secret" not in rendered


def test_chat_stream_is_ndjson_typed_and_tool_selection_is_bounded(settings: ServiceSettings) -> None:
    adapter = FakeAdapter()
    client = TestClient(create_app(settings, adapter=adapter))
    response = client.post(
        "/chat/stream",
        headers={"X-Session-ID": "web-session-1"},
        json={
            "session_id": "web-session-1",
            "turn_id": "turn-1",
            "tool_names": ["get_profile"],
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = _events(response.text)
    assert [event["kind"] for event in events] == [
        "ready",
        "agentMessageDelta",
        "agentMessageDelta",
        "agentMessageCompleted",
        "turnCompleted",
    ]
    assert [event["sequence"] for event in events] == [1, 2, 3, 4, 5]
    assert events[3]["payload"]["text"] == "namaste farmer"
    assert [tool["name"] for tool in adapter.seen_tools] == ["get_profile"]
    assert adapter.closed is True


def test_chat_input_is_bounded(settings: ServiceSettings) -> None:
    bounded = ServiceSettings(
        dev_mode=True,
        tool_contract_path=settings.tool_contract_path,
        max_input_bytes=4,
    )
    client = TestClient(create_app(bounded))
    response = client.post(
        "/chat/stream", json={"messages": [{"role": "user", "content": "12345"}]}
    )
    assert response.status_code == 413


def test_registry_rejects_more_than_configured_bound(tmp_path: Path) -> None:
    path = tmp_path / "tools.json"
    tool = {
        "name": "tool",
        "description": "bounded test tool",
        "access": "read",
        "input_schema": {"type": "object"},
    }
    path.write_text(json.dumps({"schema_version": 1, "tools": [tool] * 79}), encoding="utf-8")

    with pytest.raises(RegistryError, match="bound"):
        ToolRegistry.from_json(path, max_tools=78)


def test_invalid_registry_fails_ready_and_tools_closed(tmp_path: Path) -> None:
    path = tmp_path / "invalid-tools.json"
    path.write_text("not-json", encoding="utf-8")
    settings = ServiceSettings(dev_mode=True, tool_contract_path=path)
    client = TestClient(create_app(settings))

    assert client.get("/readyz").status_code == 503
    assert client.get("/tools").status_code == 503
