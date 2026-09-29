from __future__ import annotations

import pytest

from app.provider_config import ProviderConfig, ProviderConfigError
from app.providers.factory import create_adapter


def config(provider: str) -> ProviderConfig:
    return ProviderConfig(provider, "model-1", ("model-1",), "LLM_KEY", "https://provider.example/v1", frozenset({"text_input", "streaming", "cancellation"}))


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini", "openai_compatible", "local"])
def test_all_provider_families_declare_normalized_capabilities(provider: str) -> None:
    adapter = create_adapter(config(provider))
    assert adapter.capabilities.provider == provider
    assert {"text_input", "streaming", "cancellation"} <= adapter.capabilities.capabilities


def test_incomplete_or_insecure_provider_configuration_fails_closed() -> None:
    with pytest.raises(ProviderConfigError):
        ProviderConfig("openai", "missing", ("model-1",), "LLM_KEY", "https://provider.example", frozenset())
    with pytest.raises(ProviderConfigError):
        ProviderConfig("openai", "model-1", ("model-1",), "", "http://provider.example", frozenset())
