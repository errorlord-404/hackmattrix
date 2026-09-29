from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


class ProviderConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    provider: str
    model_alias: str
    model_allowlist: tuple[str, ...]
    secret_ref: str
    base_url: str
    capabilities: frozenset[str]
    timeout_seconds: float = 30.0
    retry_budget: int = 2
    cancellation: str = "best_effort"

    def __post_init__(self) -> None:
        if self.provider not in {"openai", "anthropic", "gemini", "openai_compatible", "local"}:
            raise ProviderConfigError("provider family is unsupported")
        if not self.model_alias or self.model_alias not in self.model_allowlist:
            raise ProviderConfigError("model alias is not allowlisted")
        if not self.secret_ref:
            raise ProviderConfigError("server-side secret reference is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ProviderConfigError("provider endpoint must use HTTPS")
        if self.timeout_seconds <= 0 or self.retry_budget < 0:
            raise ProviderConfigError("provider timeout/retry settings are invalid")

    @classmethod
    def from_env(cls, prefix: str = "KISANSATHI_LLM") -> "ProviderConfig":
        provider = os.getenv(f"{prefix}_PROVIDER", "openai_compatible").strip().lower()
        model = os.getenv(f"{prefix}_MODEL", "").strip()
        allowlist = tuple(filter(None, os.getenv(f"{prefix}_MODEL_ALLOWLIST", model).split(",")))
        return cls(provider=provider, model_alias=model, model_allowlist=allowlist, secret_ref=os.getenv(f"{prefix}_SECRET_REF", "LLM_API_KEY"), base_url=os.getenv(f"{prefix}_BASE_URL", "https://api.openai.com/v1"), capabilities=frozenset({"text_input", "streaming", "cancellation"}), timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT_SECONDS", "30")), retry_budget=int(os.getenv(f"{prefix}_RETRY_BUDGET", "2")))
