from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def default_tool_contract_path() -> Path:
    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[1] / "harness" / "contracts" / "tool-registry.json",
        Path.cwd() / "harness" / "contracts" / "tool-registry.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    # Keep a deterministic path for readiness diagnostics when the contract is
    # missing; callers fail closed rather than importing a parent tree.
    return candidates[0]


def default_model_catalog_path() -> Path:
    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[1] / "models" / "catalog.json",
        Path.cwd() / "models" / "catalog.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    """Runtime configuration. Credentials are intentionally excluded from repr."""

    environment: str = "development"
    dev_mode: bool = False
    bearer_token: str = field(default="", repr=False)
    session_secret: str = field(default="", repr=False)
    csrf_secret: str = field(default="", repr=False)
    session_kid: str = "primary"
    session_ttl_seconds: int = 3600
    csrf_ttl_seconds: int = 3600
    session_cookie_name: str = "kisansathi_session"
    csrf_cookie_name: str = "kisansathi_csrf"
    auth_state_cookie_name: str = "kisansathi_auth_state"
    auth_mode: str = ""
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = field(default="", repr=False)
    oidc_redirect_uri: str = ""
    oidc_discovery_url: str = ""
    oidc_algorithms: tuple[str, ...] = ("RS256",)
    frontend_origin: str = "/"
    internal_context_secret: str = field(default="", repr=False)
    internal_context_audience: str = "kisansathi-api"
    llm_base_url: str = ""
    llm_api_key: str = field(default="", repr=False)
    llm_model: str = ""
    tool_contract_path: Path | None = None
    model_catalog_path: Path | None = None
    max_input_bytes: int = 200_000
    max_tools: int = 78

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        return cls(
            environment=os.getenv("KISANSATHI_ENV", "development").strip().lower(),
            dev_mode=_as_bool(os.getenv("KISANSATHI_DEV_MODE")),
            bearer_token=_first_env("KISANSATHI_WEB_BEARER_TOKEN"),
            session_secret=_first_env("KISANSATHI_SESSION_SECRET") or "",
            csrf_secret=_first_env("KISANSATHI_CSRF_SECRET") or "",
            session_kid=_first_env("KISANSATHI_SESSION_KID") or "primary",
            session_ttl_seconds=max(60, min(86_400, int(os.getenv("KISANSATHI_SESSION_TTL_SECONDS", "3600")))),
            csrf_ttl_seconds=max(60, min(86_400, int(os.getenv("KISANSATHI_CSRF_TTL_SECONDS", "3600")))),
            session_cookie_name=_first_env("KISANSATHI_SESSION_COOKIE") or "kisansathi_session",
            csrf_cookie_name=_first_env("KISANSATHI_CSRF_COOKIE") or "kisansathi_csrf",
            auth_state_cookie_name=_first_env("KISANSATHI_AUTH_STATE_COOKIE") or "kisansathi_auth_state",
            auth_mode=_first_env("KISANSATHI_AUTH_MODE").strip().lower(),
            oidc_issuer=_first_env("KISANSATHI_OIDC_ISSUER"),
            oidc_audience=_first_env("KISANSATHI_OIDC_AUDIENCE"),
            oidc_client_id=_first_env("KISANSATHI_OIDC_CLIENT_ID"),
            oidc_client_secret=_first_env("KISANSATHI_OIDC_CLIENT_SECRET"),
            oidc_redirect_uri=_first_env("KISANSATHI_OIDC_REDIRECT_URI"),
            oidc_discovery_url=_first_env("KISANSATHI_OIDC_DISCOVERY_URL"),
            oidc_algorithms=tuple(filter(None, (_first_env("KISANSATHI_OIDC_ALGORITHMS") or "RS256").split(","))),
            frontend_origin=_first_env("KISANSATHI_FRONTEND_ORIGIN") or "/",
            internal_context_secret=_first_env("KISANSATHI_INTERNAL_CONTEXT_SECRET"),
            internal_context_audience=_first_env("KISANSATHI_INTERNAL_CONTEXT_AUDIENCE") or "kisansathi-api",
            llm_base_url=_first_env("KISANSATHI_LLM_BASE_URL", "OPENAI_BASE_URL").strip(),
            llm_api_key=_first_env("KISANSATHI_LLM_API_KEY", "OPENAI_API_KEY"),
            llm_model=_first_env("KISANSATHI_LLM_MODEL", "OPENAI_MODEL").strip(),
            tool_contract_path=Path(
                os.getenv("KISANSATHI_TOOL_CONTRACT_PATH", str(default_tool_contract_path()))
            ),
            model_catalog_path=Path(
                os.getenv("KISANSATHI_MODEL_CATALOG_PATH", str(default_model_catalog_path()))
            ),
            max_input_bytes=max(1, int(os.getenv("KISANSATHI_MAX_INPUT_BYTES", "200000"))),
            max_tools=max(0, min(78, int(os.getenv("KISANSATHI_MAX_TOOLS", "78")))),
        )

    @property
    def provider_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)

    @property
    def auth_required(self) -> bool:
        # A development environment is still protected unless opt-in dev mode
        # is explicitly enabled. Production can never bypass bearer auth.
        return self.environment == "production" or not (
            self.dev_mode and self.environment != "production"
        )

    @property
    def test_issuer_enabled(self) -> bool:
        return self.dev_mode and self.environment != "production" and self.auth_mode in {"test", "development"}

    @property
    def oidc_configured(self) -> bool:
        return bool(
            self.oidc_issuer
            and self.oidc_audience
            and self.oidc_client_id
            and self.oidc_client_secret
            and self.oidc_redirect_uri
        )

    @property
    def session_configured(self) -> bool:
        if self.dev_mode and self.environment != "production" and not self.session_secret and not self.csrf_secret:
            return True
        return len(self.session_secret.encode("utf-8")) >= 16 and len(self.csrf_secret.encode("utf-8")) >= 16

    @property
    def production_auth_configured(self) -> bool:
        return self.oidc_configured and self.session_configured and bool(self.internal_context_secret)
