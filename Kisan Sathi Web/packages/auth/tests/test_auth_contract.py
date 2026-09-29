from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import httpx
import jwt
import pytest


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from kisansathi_auth.claims import ActorScope, ClaimsValidationError, actor_scope_bytes, scope_from_claims  # noqa: E402
from kisansathi_auth.csrf import CsrfError, CsrfTokenCodec, require_csrf  # noqa: E402
from kisansathi_auth.oidc import AuthorizationStateStore, OIDCConfig, OIDCVerifier  # noqa: E402
from kisansathi_auth.session import InvalidSession, SessionCodec  # noqa: E402


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _claims(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "iss": "https://issuer.example.test",
        "aud": "kisansathi-web",
        "sub": "subject-1",
        "sid": "session-1",
        "tenant_id": "tenant-1",
        "farmer_id": "farmer-1",
        "roles": ["farmer"],
        "iat": 1_700_000_000,
        "exp": 1_700_000_600,
        "nonce": "nonce-1",
    }
    value.update(overrides)
    return value


def test_claims_are_complete_immutable_and_canonical() -> None:
    scope = scope_from_claims(_claims())

    assert scope == ActorScope(
        sub="subject-1",
        tenant_id="tenant-1",
        farmer_id="farmer-1",
        roles=("farmer",),
        session_id="session-1",
    )
    assert json.loads(actor_scope_bytes(scope)) == {
        "farmer_id": "farmer-1",
        "roles": ["farmer"],
        "session_id": "session-1",
        "sub": "subject-1",
        "tenant_id": "tenant-1",
    }
    with pytest.raises(AttributeError):
        scope.farmer_id = "attacker"  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"sub": None},
        {"tenant_id": ""},
        {"farmer_id": "farmer with spaces"},
        {"roles": "farmer"},
        {"sid": None},
    ],
)
def test_incomplete_or_invalid_claims_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ClaimsValidationError):
        scope_from_claims(_claims(**changes))


def test_session_cookie_is_signed_short_lived_and_rotation_compatible() -> None:
    scope = ActorScope("subject-1", "tenant-1", "farmer-1", ("farmer",), "session-1")
    codec = SessionCodec(
        {"old": b"old-session-secret-that-is-long-enough", "new": b"new-session-secret-that-is-long-enough"},
        active_kid="new",
        ttl_seconds=60,
    )

    old_token = codec.encode(scope, now=1_700_000_000, kid="old")
    assert codec.decode(old_token, now=1_700_000_030) == scope
    assert codec.decode(codec.encode(scope, now=1_700_000_030), now=1_700_000_030) == scope
    with pytest.raises(InvalidSession):
        codec.decode(old_token, now=1_700_000_061)
    with pytest.raises(InvalidSession):
        codec.decode(old_token.rsplit(".", 1)[0] + ".tampered", now=1_700_000_030)


def test_csrf_is_required_for_unsafe_cookie_methods_and_bound_to_session() -> None:
    csrf = CsrfTokenCodec(b"csrf-secret-that-is-long-enough", ttl_seconds=60)
    token = csrf.issue("session-1", now=1_700_000_000)

    assert require_csrf("GET", "session-cookie", token, token, csrf=csrf, session_id="session-1", now=1_700_000_030)
    assert require_csrf("POST", "session-cookie", token, token, csrf=csrf, session_id="session-1", now=1_700_000_030)
    with pytest.raises(CsrfError):
        require_csrf("POST", "session-cookie", token, None, csrf=csrf, session_id="session-1", now=1_700_000_030)
    with pytest.raises(CsrfError):
        require_csrf("DELETE", "session-cookie", token, token, csrf=csrf, session_id="other", now=1_700_000_030)


def test_oidc_discovery_jwks_verification_and_key_rotation() -> None:
    secret_one = b"issuer-key-one"
    secret_two = b"issuer-key-two"
    current = {"kid": "one", "secret": secret_one}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": "https://issuer.example.test",
                    "authorization_endpoint": "https://issuer.example.test/authorize",
                    "token_endpoint": "https://issuer.example.test/token",
                    "jwks_uri": "https://issuer.example.test/jwks",
                },
            )
        if request.url.path == "/jwks":
            return httpx.Response(
                200,
                json={
                    "keys": [
                        {
                            "kty": "oct",
                            "kid": current["kid"],
                            "alg": "HS256",
                            "k": _b64(current["secret"]),
                        }
                    ]
                },
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    verifier = OIDCVerifier(
        OIDCConfig(
            issuer="https://issuer.example.test",
            audience="kisansathi-web",
            client_id="client-1",
            client_secret="provider-secret",
            redirect_uri="https://web.example.test/auth/callback",
            algorithms=("HS256",),
        ),
        client=client,
    )

    first = jwt.encode(_claims(), secret_one, algorithm="HS256", headers={"kid": "one"})
    assert verifier.verify_id_token(first, nonce="nonce-1", now=1_700_000_030).farmer_id == "farmer-1"

    current.update(kid="two", secret=secret_two)
    rotated = jwt.encode(_claims(nonce="nonce-2"), secret_two, algorithm="HS256", headers={"kid": "two"})
    assert verifier.verify_id_token(rotated, nonce="nonce-2", now=1_700_000_030).session_id == "session-1"

    wrong_issuer = jwt.encode(_claims(iss="https://attacker.example.test"), secret_two, algorithm="HS256", headers={"kid": "two"})
    with pytest.raises(Exception):
        verifier.verify_id_token(wrong_issuer, nonce="nonce-1", now=1_700_000_030)

    wrong_algorithm = jwt.encode(_claims(), secret_two, algorithm="HS384", headers={"kid": "two"})
    with pytest.raises(Exception):
        verifier.verify_id_token(wrong_algorithm, nonce="nonce-1", now=1_700_000_030)


def test_oidc_authorization_state_contains_pkce_and_is_single_use() -> None:
    states = AuthorizationStateStore(ttl_seconds=120)
    pending = states.create(redirect_uri="https://web.example.test/auth/callback", now=1_700_000_000)

    assert pending.state
    assert pending.nonce
    assert pending.code_verifier
    assert pending.code_challenge
    consumed = states.consume(pending.state, now=1_700_000_001)
    assert consumed.code_verifier == pending.code_verifier
    with pytest.raises(KeyError):
        states.consume(pending.state, now=1_700_000_001)
