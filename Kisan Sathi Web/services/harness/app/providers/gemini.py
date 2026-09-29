from __future__ import annotations

from typing import Any

from .base import ProviderText, ProviderToolCall, ProviderFailure
from .openai_compatible import OpenAICompatibleAdapter


class GeminiAdapter(OpenAICompatibleAdapter):
    provider_name = "gemini"

    @staticmethod
    def normalize_chunk(chunk: dict[str, Any]):
        if chunk.get("error"): return ProviderFailure(str((chunk.get("error") or {}).get("status", "provider_error")))
        for part in (chunk.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
            if part.get("text"): return ProviderText(str(part["text"]))
            if part.get("functionCall"): return ProviderToolCall(str(part["functionCall"].get("name", "tool")), part["functionCall"].get("args", {}) or {}, str(chunk.get("responseId", "tool-call")))
        return None
