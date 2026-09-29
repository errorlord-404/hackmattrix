from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings
from .errors import BackendError, is_retryable_status


@dataclass(frozen=True, slots=True)
class BackendResponse:
    data: Any
    request_id: str
    status_code: int


class BackendClient:
    """Small HTTP boundary that keeps farmer identity out of tool arguments."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.backend_url,
            timeout=httpx.Timeout(settings.timeout_seconds),
            transport=transport,
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "BackendClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        content: bytes | None = None,
        content_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> BackendResponse:
        request_id = str(uuid.uuid4())
        headers = {
            "Accept": "application/json",
            "X-Farmer-ID": self.settings.farmer_id,
            "X-Request-ID": request_id,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if content_type:
            headers["Content-Type"] = content_type

        try:
            response = await self._client.request(
                method,
                path,
                params={key: value for key, value in (params or {}).items() if value is not None},
                json=None if content is not None else json,
                content=content,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise BackendError(
                message="The farming service timed out.",
                code="backend_timeout",
                retryable=True,
                request_id=request_id,
            ) from exc
        except httpx.RequestError as exc:
            raise BackendError(
                message="The farming service is unreachable.",
                code="backend_unreachable",
                retryable=True,
                request_id=request_id,
            ) from exc

        response_request_id = response.headers.get("X-Request-ID", request_id)
        if response.is_error:
            detail: Any = None
            try:
                payload = response.json()
                detail = payload.get("detail") if isinstance(payload, dict) else payload
            except ValueError:
                detail = None
            code = "backend_http_error"
            message = f"The farming service returned HTTP {response.status_code}."
            if isinstance(detail, dict):
                code = str(detail.get("code") or code)
                message = str(detail.get("message") or message)
            elif isinstance(detail, str) and detail:
                message = detail
            raise BackendError(
                message=message,
                code=code,
                status_code=response.status_code,
                retryable=is_retryable_status(response.status_code),
                request_id=response_request_id,
            )

        if response.status_code == 204:
            payload = None
        else:
            try:
                payload = response.json()
            except ValueError as exc:
                raise BackendError(
                    message="The farming service returned an invalid response.",
                    code="backend_invalid_response",
                    status_code=response.status_code,
                    request_id=response_request_id,
                ) from exc
        return BackendResponse(payload, response_request_id, response.status_code)

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> BackendResponse:
        return await self.request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: Any,
        idempotency_key: str,
    ) -> BackendResponse:
        return await self.request("POST", path, json=json, idempotency_key=idempotency_key)

    async def post_bytes(
        self,
        path: str,
        *,
        content: bytes,
        content_type: str,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> BackendResponse:
        return await self.request(
            "POST",
            path,
            params=params,
            content=content,
            content_type=content_type,
            idempotency_key=idempotency_key,
        )

    async def put(
        self,
        path: str,
        *,
        json: Any,
        idempotency_key: str,
    ) -> BackendResponse:
        return await self.request("PUT", path, json=json, idempotency_key=idempotency_key)

    async def patch(
        self,
        path: str,
        *,
        json: Any,
        idempotency_key: str,
    ) -> BackendResponse:
        return await self.request("PATCH", path, json=json, idempotency_key=idempotency_key)
