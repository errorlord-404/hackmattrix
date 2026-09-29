from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LLMChunk:
    text: str = ""
    finish_reason: str | None = None


class LLMAdapterError(RuntimeError):
    """Safe adapter error; callers must not expose the original exception."""

    def __init__(self, code: str, *, retryable: bool) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class LLMAdapter(Protocol):
    provider_name: str
    configured: bool

    def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        tools: Sequence[Mapping[str, Any]],
    ) -> AsyncIterator[LLMChunk]: ...

    async def aclose(self) -> None: ...

