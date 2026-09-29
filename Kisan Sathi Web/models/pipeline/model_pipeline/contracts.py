"""Dependency-light contracts shared by model lifecycle commands."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PipelineError(ValueError):
    """Raised when lifecycle input fails a deterministic contract."""


def load_json(path: Path, label: str = "JSON document") -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PipelineError(f"unable to read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise PipelineError(f"{label} must be a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(root: Path, value: str, field: str = "path") -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise PipelineError(f"{field} must be a non-empty relative path without parent traversal")
    root = Path(root).resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PipelineError(f"{field} escapes its root") from exc
    return candidate


def validate_schema(document: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError as exc:
        raise PipelineError("registry validation requires jsonschema; install requirements-core.txt") from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise PipelineError(f"{label} schema validation failed: {detail}")

