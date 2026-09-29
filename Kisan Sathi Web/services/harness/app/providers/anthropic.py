from __future__ import annotations

from typing import Any

from .base import ProviderText, ProviderToolCall, ProviderFailure
from .openai_compatible import OpenAICompatibleAdapter


class AnthropicAdapter(OpenAICompatibleAdapter):
    provider_name = "anthropic"

    @staticmethod
    def normalize_chunk(chunk: dict[str, Any]):
        kind = chunk.get("type")
        if kind == "content_block_delta":
            delta = chunk.get("delta") or {}
            if delta.get("type") == "text_delta": return ProviderText(str(delta.get("text", "")))
        if kind == "content_block_start":
            block = chunk.get("content_block") or {}
            if block.get("type") == "tool_use": return ProviderToolCall(str(block.get("name", "tool")), block.get("input", {}) if isinstance(block.get("input", {}), dict) else {}, str(block.get("id", "tool-call")))
        if kind == "error": return ProviderFailure(str((chunk.get("error") or {}).get("type", "provider_error")))
        return None
