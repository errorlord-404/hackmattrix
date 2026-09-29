from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from typing import Any

from app.provider_config import ProviderConfig
from .base import ProviderCapabilities, ProviderFailure, ProviderRequest, ProviderText, ProviderToolCall


class OpenAICompatibleAdapter:
    provider_name = "openai_compatible"

    def __init__(self, config: ProviderConfig, *, chunks: Iterable[dict[str, Any]] | None = None) -> None:
        self.config = config
        self.chunks = tuple(chunks or ())
        self.capabilities = ProviderCapabilities(self.provider_name, config.model_alias, config.capabilities)
        self.cancelled = False

    @staticmethod
    def normalize_chunk(chunk: dict[str, Any]):
        if "error" in chunk:
            error = chunk.get("error") if isinstance(chunk.get("error"), dict) else {}
            return ProviderFailure(str(error.get("code", "provider_error")), retryable=bool(error.get("retryable", False)))
        choice = (chunk.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        if delta.get("content"):
            return ProviderText(str(delta["content"]))
        call = (delta.get("tool_calls") or [{}])[0]
        function = call.get("function") or {}
        if function.get("name"):
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                import json
                try: arguments = json.loads(arguments)
                except json.JSONDecodeError: return ProviderFailure("malformed_tool_arguments")
            return ProviderToolCall(str(function["name"]), arguments if isinstance(arguments, dict) else {}, str(call.get("id", "tool-call")))
        return None

    async def stream_turn(self, request: ProviderRequest) -> AsyncIterator[ProviderText | ProviderToolCall | ProviderFailure]:
        for chunk in self.chunks:
            if self.cancelled: return
            await asyncio.sleep(0)
            event = self.normalize_chunk(chunk)
            if event is not None: yield event

    async def cancel(self, turn_id: str) -> None:
        self.cancelled = True
