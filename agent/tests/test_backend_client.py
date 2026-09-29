from __future__ import annotations

import asyncio

import httpx
import pytest

from kisansathi_agent.backend_client import BackendClient
from kisansathi_agent.config import Settings
from kisansathi_agent.errors import BackendError


def run(coro):
    return asyncio.run(coro)


def settings() -> Settings:
    return Settings(backend_url="http://backend.test", farmer_id="farmer-1")


def test_client_attaches_farmer_and_request_identity() -> None:
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["params"] = request.url.params
        return httpx.Response(200, json={"ok": True}, headers={"X-Request-ID": "server-request"})

    async def scenario() -> None:
        client = BackendClient(settings(), transport=httpx.MockTransport(handler))
        response = await client.get("/v1/profile", params={"unused": None, "include": True})
        assert response.data == {"ok": True}
        assert response.request_id == "server-request"
        assert seen["headers"]["x-farmer-id"] == "farmer-1"
        assert seen["headers"]["x-request-id"]
        assert str(seen["params"]) == "include=true"
        await client.aclose()

    run(scenario())


def test_client_maps_backend_errors_without_leaking_body() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"detail": {"code": "weather_provider_unavailable", "message": "provider offline", "secret": "redact"}},
        )

    async def scenario() -> None:
        client = BackendClient(settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(BackendError) as raised:
            await client.get("/v1/weather")
        assert raised.value.code == "weather_provider_unavailable"
        assert raised.value.message == "provider offline"
        assert "secret" not in str(raised.value)
        assert raised.value.retryable is True
        await client.aclose()

    run(scenario())

