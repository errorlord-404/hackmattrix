from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from .claims import ActorScope, ClaimsValidationError, scope_from_claims


class OIDCVerificationError(ValueError):
    """Raised when discovery, token exchange, or ID-token verification fails."""


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True, slots=True)
class OIDCConfig:
    issuer: str
    audience: str
    client_id: str
    client_secret: str
    redirect_uri: str
    discovery_url: str | None = None
    scope: str = "openid profile email"
    algorithms: tuple[str, ...] = ("RS256",)
    clock_skew_seconds: int = 30
    jwks_cache_seconds: int = 300


@dataclass(frozen=True, slots=True)
class AuthorizationState:
    state: str
    nonce: str
    code_verifier: str
    code_challenge: str
    redirect_uri: str
    created_at: int


class AuthorizationStateStore:
    def __init__(self, *, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = max(30, min(int(ttl_seconds), 900))
        self._values: dict[str, AuthorizationState] = {}
        self._lock = threading.Lock()

    def create(self, *, redirect_uri: str, now: int | None = None) -> AuthorizationState:
        issued = int(time.time() if now is None else now)
        verifier = _b64(secrets.token_bytes(32))
        value = AuthorizationState(
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            code_verifier=verifier,
            code_challenge=_b64(hashlib.sha256(verifier.encode("ascii")).digest()),
            redirect_uri=redirect_uri,
            created_at=issued,
        )
        with self._lock:
            self._values[value.state] = value
        return value

    def consume(self, state: str, *, now: int | None = None) -> AuthorizationState:
        current = int(time.time() if now is None else now)
        with self._lock:
            value = self._values.pop(state, None)
        if value is None or current > value.created_at + self.ttl_seconds:
            raise KeyError("authorization state is missing or expired")
        return value


class _JWKSCache:
    def __init__(self) -> None:
        self.fetched_at = 0.0
        self.document: dict[str, Any] | None = None


class OIDCVerifier:
    def __init__(self, config: OIDCConfig, *, client: httpx.Client | None = None) -> None:
        if not config.issuer or not config.audience or not config.client_id or not config.redirect_uri:
            raise ValueError("OIDC issuer, audience, client identity, and redirect URI are required")
        if not config.algorithms or any(algorithm not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "HS256"} for algorithm in config.algorithms):
            raise ValueError("OIDC algorithms must use the explicit supported allowlist")
        self.config = config
        self.client = client or httpx.Client(timeout=httpx.Timeout(10.0))
        self._owns_client = client is None
        self._discovery: dict[str, Any] | None = None
        self._jwks = _JWKSCache()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def discovery(self) -> dict[str, Any]:
        if self._discovery is not None:
            return self._discovery
        url = self.config.discovery_url or self.config.issuer.rstrip("/") + "/.well-known/openid-configuration"
        try:
            response = self.client.get(url)
            response.raise_for_status()
            document = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OIDCVerificationError("OIDC discovery is unavailable") from exc
        if not isinstance(document, dict) or document.get("issuer") != self.config.issuer:
            raise OIDCVerificationError("OIDC discovery issuer does not match configured issuer")
        for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            if not isinstance(document.get(field), str) or not document[field]:
                raise OIDCVerificationError("OIDC discovery is incomplete")
        self._discovery = document
        return document

    def authorization_url(self, pending: AuthorizationState) -> str:
        document = self.discovery()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.config.client_id,
                "redirect_uri": pending.redirect_uri,
                "scope": self.config.scope,
                "state": pending.state,
                "nonce": pending.nonce,
                "code_challenge": pending.code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{document['authorization_endpoint']}?{query}"

    def exchange_code(self, code: str, pending: AuthorizationState) -> dict[str, Any]:
        if not code or len(code) > 4096:
            raise OIDCVerificationError("authorization code is invalid")
        document = self.discovery()
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": pending.redirect_uri,
            "code_verifier": pending.code_verifier,
        }
        try:
            response = self.client.post(document["token_endpoint"], data=form)
            response.raise_for_status()
            token_response = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OIDCVerificationError("authorization code exchange failed") from exc
        if not isinstance(token_response, dict) or not isinstance(token_response.get("id_token"), str):
            raise OIDCVerificationError("authorization response did not contain an ID token")
        return token_response

    def _jwks_document(self, *, force: bool = False) -> dict[str, Any]:
        current = time.monotonic()
        if not force and self._jwks.document is not None and current - self._jwks.fetched_at < self.config.jwks_cache_seconds:
            return self._jwks.document
        try:
            response = self.client.get(self.discovery()["jwks_uri"])
            response.raise_for_status()
            document = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OIDCVerificationError("OIDC signing keys are unavailable") from exc
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            raise OIDCVerificationError("OIDC signing keys are invalid")
        self._jwks.document = document
        self._jwks.fetched_at = current
        return document

    def _key_for(self, token: str) -> Any:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise OIDCVerificationError("ID token header is invalid") from exc
        algorithm = header.get("alg")
        kid = header.get("kid")
        if algorithm not in self.config.algorithms or not isinstance(kid, str) or not kid:
            raise OIDCVerificationError("ID token algorithm or key identifier is not allowed")
        document = self._jwks_document()
        jwk = next((item for item in document["keys"] if isinstance(item, dict) and item.get("kid") == kid), None)
        if jwk is None:
            document = self._jwks_document(force=True)
            jwk = next((item for item in document["keys"] if isinstance(item, dict) and item.get("kid") == kid), None)
        if not isinstance(jwk, dict) or (jwk.get("alg") and jwk.get("alg") != algorithm):
            raise OIDCVerificationError("OIDC signing key is not available")
        try:
            if jwk.get("kty") == "oct":
                return _unb64(str(jwk["k"]))
            if jwk.get("kty") == "RSA":
                return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            if jwk.get("kty") == "EC":
                return jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(jwk))
        except (KeyError, TypeError, ValueError) as exc:
            raise OIDCVerificationError("OIDC signing key is malformed") from exc
        raise OIDCVerificationError("OIDC signing key type is not supported")

    def verify_id_token(self, token: str, *, nonce: str | None = None, now: int | None = None) -> ActorScope:
        if not isinstance(token, str) or len(token) > 32_768:
            raise OIDCVerificationError("ID token is invalid")
        key = self._key_for(token)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=list(self.config.algorithms),
                options={
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                    "verify_aud": False,
                    "verify_iss": False,
                    "require": ["iss", "aud", "sub", "sid", "tenant_id", "farmer_id", "roles", "iat", "exp"],
                },
            )
        except jwt.PyJWTError as exc:
            raise OIDCVerificationError("ID token signature is invalid") from exc
        if claims.get("iss") != self.config.issuer:
            raise OIDCVerificationError("ID token issuer is invalid")
        audience = claims.get("aud")
        if not (audience == self.config.audience or isinstance(audience, list) and self.config.audience in audience):
            raise OIDCVerificationError("ID token audience is invalid")
        current = int(time.time() if now is None else now)
        exp = claims.get("exp")
        issued = claims.get("iat")
        if not isinstance(exp, (int, float)) or not isinstance(issued, (int, float)):
            raise OIDCVerificationError("ID token time claims are invalid")
        skew = max(0, int(self.config.clock_skew_seconds))
        if current > int(exp) + skew or current < int(issued) - skew:
            raise OIDCVerificationError("ID token is expired or not yet valid")
        nbf = claims.get("nbf")
        if nbf is not None and (not isinstance(nbf, (int, float)) or current < int(nbf) - skew):
            raise OIDCVerificationError("ID token is not yet valid")
        if nonce is not None and claims.get("nonce") != nonce:
            raise OIDCVerificationError("ID token nonce is invalid")
        try:
            return scope_from_claims(claims)
        except ClaimsValidationError as exc:
            raise OIDCVerificationError("ID token identity claims are incomplete") from exc
