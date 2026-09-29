from __future__ import annotations

import os
import re
from typing import Any


SECRET_KEYS = re.compile(r"(?:api[-_]?key|authorization|access[-_]?token|refresh[-_]?token|client[-_]?secret|password|credential|secret|cookie)", re.IGNORECASE)


def load_secret(reference: str) -> str:
    value = os.getenv(reference)
    if not value:
        raise RuntimeError(f"required provider secret is unavailable: {reference}")
    return value


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): "[REDACTED]" if SECRET_KEYS.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, list): return [redact(item) for item in value]
    if isinstance(value, tuple): return [redact(item) for item in value]
    if isinstance(value, str) and SECRET_KEYS.search(value): return "[REDACTED]"
    return value
