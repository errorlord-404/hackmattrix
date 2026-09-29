from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .provider_config import ProviderConfig
from .providers.base import ProviderAdapter, ProviderCapabilities
from .providers.factory import create_adapter
from .secrets import load_secret


@dataclass(frozen=True, slots=True)
class ProviderRuntime:
    config: ProviderConfig
    adapter: ProviderAdapter
    capabilities: ProviderCapabilities

    @classmethod
    def from_config(cls, config: ProviderConfig, *, chunks: Iterable[dict[str, Any]] = (), resolve_secret: bool = True) -> "ProviderRuntime":
        if resolve_secret:
            load_secret(config.secret_ref)
        adapter = create_adapter(config, chunks=chunks)
        return cls(config, adapter, adapter.capabilities)

    def public_capabilities(self) -> dict[str, Any]:
        return {"provider": self.config.provider, "model": self.config.model_alias, "capabilities": sorted(self.capabilities.capabilities), "status": "configured"}
