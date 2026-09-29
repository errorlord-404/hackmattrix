from __future__ import annotations

import asyncio
import json

import httpx

from app.adapters.openai_compatible import OpenAICompatibleAdapter


def test_openai_compatible_adapter_parses_sse_without_leaking_credentials() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["authorization"]
        seen["payload"] = json.loads(request.content)
        body = (
            'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body.encode(),
        )

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    adapter = OpenAICompatibleAdapter(
        base_url="https://llm.example/v1",
        api_key="secret-value",
        model="server-model",
        client_factory=factory,
    )

    async def collect() -> list[str]:
        return [
            chunk.text
            async for chunk in adapter.stream_chat(
                [{"role": "user", "content": "hi"}], []
            )
        ]

    assert asyncio.run(collect()) == ["hello", " world"]
    assert seen["authorization"] == "Bearer secret-value"
    assert seen["payload"]["model"] == "server-model"  # type: ignore[index]
    assert "secret-value" not in adapter.provider_name


def test_openai_compatible_adapter_translates_provider_neutral_tool_schema() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, content=b"data: [DONE]\n\n")

    adapter = OpenAICompatibleAdapter(
        base_url="https://llm.example/v1",
        api_key="server-secret",
        model="server-model",
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    async def consume() -> None:
        async for _ in adapter.stream_chat(
            [{"role": "user", "content": "hi"}],
            [{"name": "get_profile", "description": "Read profile", "input_schema": {"type": "object"}}],
        ):
            pass

    asyncio.run(consume())
    tool = seen["payload"]["tools"][0]["function"]  # type: ignore[index]
    assert tool["name"] == "get_profile"
    assert tool["parameters"] == {"type": "object"}
    assert "input_schema" not in tool


def test_openai_compatible_adapter_is_unconfigured_without_all_server_values() -> None:
    adapter = OpenAICompatibleAdapter(base_url="", api_key="", model="")
    assert adapter.configured is False


def test_openai_compatible_adapter_propagates_cancellation_and_closes_client() -> None:
    class CancelledClient:
        closed = False

        def stream(self, *args: object, **kwargs: object) -> "CancelledClient":
            return self

        async def __aenter__(self) -> "CancelledClient":
            raise asyncio.CancelledError

        async def __aexit__(self, *args: object) -> None:
            return None

        async def aclose(self) -> None:
            self.closed = True

    client = CancelledClient()
    adapter = OpenAICompatibleAdapter(
        base_url="https://llm.example/v1",
        api_key="server-secret",
        model="server-model",
        client_factory=lambda: client,  # type: ignore[arg-type]
    )

    async def consume() -> None:
        async for _ in adapter.stream_chat([], []):
            pass

    try:
        asyncio.run(consume())
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("cancellation was converted into a normal result")
    assert client.closed is True
