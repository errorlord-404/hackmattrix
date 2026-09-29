from __future__ import annotations

import asyncio

from app.provider_config import ProviderConfig
from app.providers.anthropic import AnthropicAdapter
from app.providers.base import ProviderRequest, ProviderText, ProviderToolCall
from app.providers.gemini import GeminiAdapter
from app.providers.openai import OpenAIAdapter
from app.providers.openai_compatible import OpenAICompatibleAdapter


def cfg(provider: str) -> ProviderConfig:
    return ProviderConfig(provider, "model-1", ("model-1",), "LLM_KEY", "https://provider.example/v1", frozenset({"text_input", "streaming", "cancellation"}))


def collect(adapter, chunks):
    adapter.chunks = tuple(chunks)
    return asyncio.run(_collect(adapter))


async def _collect(adapter):
    values = []
    async for item in adapter.stream_turn(ProviderRequest(({"role": "user", "content": "hello"},))): values.append(item)
    return values


def test_provider_specific_wire_shapes_normalize_to_common_events() -> None:
    assert collect(OpenAIAdapter(cfg("openai")), [{"type": "response.output_text.delta", "delta": "hello"}]) == [ProviderText("hello")]
    assert collect(AnthropicAdapter(cfg("anthropic")), [{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hello"}}]) == [ProviderText("hello")]
    assert collect(GeminiAdapter(cfg("gemini")), [{"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}]) == [ProviderText("hello")]
    assert collect(OpenAICompatibleAdapter(cfg("openai_compatible")), [{"choices": [{"delta": {"content": "hello"}}]}]) == [ProviderText("hello")]


def test_tool_calls_normalize_without_provider_wire_fields() -> None:
    event = OpenAIAdapter.normalize_chunk({"type": "response.function_call_arguments.done", "name": "get_profile", "arguments": {}, "call_id": "call-1"})
    assert event == ProviderToolCall("get_profile", {}, "call-1")
