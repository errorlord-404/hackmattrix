from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from .base import LLMAdapterError, LLMChunk


class OpenAICompatibleAdapter:
    """Streaming adapter for APIs implementing /chat/completions semantics."""

    provider_name = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=timeout_seconds)
        )

    @property
    def configured(self) -> bool:
        parsed = urlparse(self.base_url)
        return bool(
            self.api_key
            and self.model
            and parsed.scheme in {"http", "https"}
            and parsed.netloc
            and not parsed.username
            and not parsed.password
        )

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        tools: Sequence[Mapping[str, Any]],
    ) -> AsyncIterator[LLMChunk]:
        if not self.configured:
            raise LLMAdapterError("provider_unavailable", retryable=False)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        # The standalone registry uses the provider-neutral
                        # input_schema name; OpenAI-compatible APIs expect
                        # JSON Schema under parameters.
                        "parameters": tool.get("input_schema", {"type": "object"}),
                    },
                }
                for tool in tools
            ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        client = self._client_factory()
        try:
            async with client.stream(
                "POST", self.endpoint, headers=headers, json=payload
            ) as response:
                if response.status_code >= 400:
                    raise LLMAdapterError(
                        "provider_http_error", retryable=response.status_code >= 500
                    )
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    data = line[5:].strip() if line.startswith("data:") else line.strip()
                    if data == "[DONE]":
                        break
                    try:
                        decoded = json.loads(data)
                    except json.JSONDecodeError:
                        # Ignore keepalive/non-JSON lines from compatible gateways.
                        continue
                    for choice in decoded.get("choices", []):
                        delta = choice.get("delta") or {}
                        content = delta.get("content", "")
                        if isinstance(content, str) and content:
                            yield LLMChunk(
                                text=content,
                                finish_reason=choice.get("finish_reason"),
                            )
        except asyncio.CancelledError:
            # Do not convert cancellation into a provider error; the async
            # context managers above close the response and client.
            raise
        except LLMAdapterError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError):
            raise LLMAdapterError("provider_network_error", retryable=True) from None
        except httpx.HTTPError:
            raise LLMAdapterError("provider_request_failed", retryable=True) from None
        finally:
            await client.aclose()

    async def aclose(self) -> None:
        """Compatibility hook for request-level lifecycle management."""
