from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Sequence
from .base import ProviderFailure, ProviderText, ProviderToolCall


class FakeProvider:
    provider_name = "fake"

    def __init__(self, events: Sequence[ProviderText | ProviderToolCall | ProviderFailure] = (), *, configured: bool = True, delay: float = 0.0) -> None:
        self.events = tuple(events)
        self.configured = configured
        self.delay = delay
        self.cancelled = False

    async def stream_turn(self, messages: Sequence[dict[str, str]], tools: Sequence[dict[str, Any]] = ()) -> AsyncIterator[ProviderText | ProviderToolCall | ProviderFailure]:
        if not self.configured:
            yield ProviderFailure("provider_unavailable", retryable=True)
            return
        for event in self.events:
            if self.cancelled:
                return
            if self.delay:
                await asyncio.sleep(self.delay)
            else:
                await asyncio.sleep(0)
            yield event

    async def cancel(self, turn_id: str) -> None:
        self.cancelled = True
