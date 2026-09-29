from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider: str
    model_alias: str
    capabilities: frozenset[str]
    max_input_bytes: int = 200_000
    max_output_tokens: int = 4096


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    messages: tuple[dict[str, str], ...]
    tools: tuple[dict[str, Any], ...] = ()
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class ProviderText:
    text: str


@dataclass(frozen=True, slots=True)
class ProviderToolCall:
    tool: str
    arguments: dict[str, Any]
    call_id: str


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    code: str
    retryable: bool = False
    message: str = "The configured provider is unavailable."


class ProviderAdapter(Protocol):
    provider_name: str
    capabilities: ProviderCapabilities

    async def stream_turn(self, request: ProviderRequest) -> AsyncIterator[ProviderText | ProviderToolCall | ProviderFailure]: ...
    async def cancel(self, turn_id: str) -> None: ...
