from __future__ import annotations

from uuid import uuid4

from kisansathi_auth.claims import ActorScope


class TestIssuerDisabled(PermissionError):
    """Raised when a test issuer is requested outside an explicit dev mode."""


def issue_scope(settings, *, sub: str, tenant_id: str, farmer_id: str, roles: tuple[str, ...] = ("farmer",), session_id: str | None = None) -> ActorScope:
    if not settings.test_issuer_enabled:
        raise TestIssuerDisabled("The test issuer is available only in explicit non-production test/development mode.")
    return ActorScope(sub=sub, tenant_id=tenant_id, farmer_id=farmer_id, roles=roles, session_id=session_id or f"test-session-{uuid4().hex}")
