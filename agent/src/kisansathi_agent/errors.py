from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BackendError(Exception):
    """Safe, model-facing representation of a backend failure."""

    message: str
    code: str
    status_code: int | None = None
    retryable: bool = False
    request_id: str | None = None

    def __str__(self) -> str:
        return self.message


def is_retryable_status(status_code: int | None) -> bool:
    return status_code is None or status_code in {408, 425, 429} or status_code >= 500

