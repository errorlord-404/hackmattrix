from __future__ import annotations

import asyncio

from app.provider_config import ProviderConfig
from app.provider_runtime import ProviderRuntime
from app.orchestrator import Orchestrator
from app.providers.base import ProviderRequest, ProviderText


def test_runtime_factory_reaches_recorded_openai_transport_without_secret_in_capabilities(monkeypatch) -> None:
    monkeypatch.setenv("LLM_KEY", "sentinel-secret")
    config = ProviderConfig("openai", "model-1", ("model-1",), "LLM_KEY", "https://provider.example/v1", frozenset({"text_input", "streaming", "cancellation"}))
    runtime = ProviderRuntime.from_config(config, chunks=[{"type": "response.output_text.delta", "delta": "hello"}])
    events = asyncio.run(_collect(runtime.adapter))
    assert events == [ProviderText("hello")]
    assert "sentinel" not in str(runtime.public_capabilities())


def test_orchestrator_accepts_validated_runtime_and_projects_safe_capabilities() -> None:
    config = ProviderConfig("gemini", "model-1", ("model-1",), "LLM_KEY", "https://provider.example/v1", frozenset({"text_input", "streaming", "cancellation"}))
    runtime = ProviderRuntime.from_config(config, chunks=[], resolve_secret=False)
    harness = Orchestrator.from_runtime(runtime)

    assert harness.public_capabilities()["provider"] == "gemini"
    assert "LLM_KEY" not in str(harness.public_capabilities())


async def _collect(adapter):
    values = []
    async for item in adapter.stream_turn(ProviderRequest(({"role": "user", "content": "hello"},))): values.append(item)
    return values
