"""Typed, bounded errors for the standalone tool boundary.

Errors in this package are intentionally safe to put in a model-visible result.
They contain stable codes and short messages, never provider bodies, credentials,
SQL, filesystem paths, or exception reprs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ToolRegistryError(Exception):
    message: str
    code: str = "tool_registry_error"
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class RegistryError(ToolRegistryError):
    pass


class ToolValidationError(ToolRegistryError):
    pass


class PolicyError(ToolRegistryError):
    pass


class ExecutionContextError(ToolRegistryError):
    pass


@dataclass(slots=True)
class BackendError(Exception):
    """Safe representation of an API failure."""

    message: str
    code: str
    status_code: int | None = None
    retryable: bool = False
    request_id: str | None = None

    def __str__(self) -> str:
        return self.message


def is_retryable_status(status_code: int | None) -> bool:
    return status_code is None or status_code in {408, 425, 429} or status_code >= 500
