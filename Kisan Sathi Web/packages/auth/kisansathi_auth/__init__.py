"""Shared authentication boundary for the standalone Kisan Sathi services."""

from .claims import ActorScope, ClaimsValidationError, actor_scope_bytes, scope_from_claims
from .csrf import CsrfError, CsrfTokenCodec, require_csrf
from .oidc import AuthorizationState, AuthorizationStateStore, OIDCConfig, OIDCVerifier, OIDCVerificationError
from .session import InvalidSession, SessionCodec, SessionRegistry

__all__ = [
    "ActorScope",
    "AuthorizationState",
    "AuthorizationStateStore",
    "ClaimsValidationError",
    "CsrfError",
    "CsrfTokenCodec",
    "InvalidSession",
    "OIDCConfig",
    "OIDCVerifier",
    "OIDCVerificationError",
    "SessionCodec",
    "SessionRegistry",
    "actor_scope_bytes",
    "require_csrf",
    "scope_from_claims",
]
