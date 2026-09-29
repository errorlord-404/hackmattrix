from __future__ import annotations

from typing import Any, Iterable

from app.provider_config import ProviderConfig
from .anthropic import AnthropicAdapter
from .base import ProviderAdapter
from .gemini import GeminiAdapter
from .local import LocalAdapter
from .openai import OpenAIAdapter
from .openai_compatible import OpenAICompatibleAdapter


def create_adapter(config: ProviderConfig, *, chunks: Iterable[dict[str, Any]] = ()) -> ProviderAdapter:
    adapters = {"openai": OpenAIAdapter, "anthropic": AnthropicAdapter, "gemini": GeminiAdapter, "openai_compatible": OpenAICompatibleAdapter, "local": LocalAdapter}
    return adapters[config.provider](config, chunks=chunks)
