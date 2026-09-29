from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ClaimsValidationError(ValueError):
    """Raised when a claims-derived actor cannot be established safely."""


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ClaimsValidationError(f"{label} must be a bounded server-issued identifier")
    return value


def _roles(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ClaimsValidationError("roles must be an array of identifiers")
    try:
        normalized = {_identifier(role, "role") for role in value}
    except TypeError as exc:
        raise ClaimsValidationError("roles must be an array of identifiers") from exc
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class ActorScope:
    """Immutable identity derived only from verified claims or signed context."""

    sub: str
    tenant_id: str
    farmer_id: str
    roles: tuple[str, ...] = ()
    session_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sub", _identifier(self.sub, "sub"))
        object.__setattr__(self, "tenant_id", _identifier(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "farmer_id", _identifier(self.farmer_id, "farmer_id"))
        object.__setattr__(self, "session_id", _identifier(self.session_id, "session_id"))
        object.__setattr__(self, "roles", _roles(self.roles))

    @property
    def actor_id(self) -> str:
        return self.sub

    def as_dict(self) -> dict[str, Any]:
        return {
            "sub": self.sub,
            "tenant_id": self.tenant_id,
            "farmer_id": self.farmer_id,
            "roles": list(self.roles),
            "session_id": self.session_id,
        }


def scope_from_claims(claims: Mapping[str, Any]) -> ActorScope:
    """Project verified OIDC claims into the only identity shape services accept."""

    if not isinstance(claims, Mapping):
        raise ClaimsValidationError("claims must be an object")
    required = ("sub", "tenant_id", "farmer_id", "roles", "sid")
    missing = [name for name in required if name not in claims]
    if missing:
        raise ClaimsValidationError("required claims are missing")
    return ActorScope(
        sub=claims["sub"],
        tenant_id=claims["tenant_id"],
        farmer_id=claims["farmer_id"],
        roles=_roles(claims["roles"]),
        session_id=claims["sid"],
    )


def actor_scope_bytes(scope: ActorScope) -> bytes:
    """Return the stable bytes shared by API and harness actor adapters."""

    if not isinstance(scope, ActorScope):
        raise TypeError("scope must be an ActorScope")
    return json.dumps(
        scope.as_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
