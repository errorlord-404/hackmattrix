from __future__ import annotations

from typing import Any

from .base import ProviderText, ProviderToolCall, ProviderFailure
from .openai_compatible import OpenAICompatibleAdapter


class OpenAIAdapter(OpenAICompatibleAdapter):
    provider_name = "openai"

    @staticmethod
    def normalize_chunk(chunk: dict[str, Any]):
        kind = chunk.get("type")
        if kind == "response.output_text.delta": return ProviderText(str(chunk.get("delta", "")))
        if kind == "response.function_call_arguments.done": return ProviderToolCall(str(chunk.get("name", "tool")), chunk.get("arguments", {}) if isinstance(chunk.get("arguments", {}), dict) else {}, str(chunk.get("call_id", "tool-call")))
        if kind == "error": return ProviderFailure(str(chunk.get("code", "provider_error")), retryable=bool(chunk.get("retryable", False)))
        return None
