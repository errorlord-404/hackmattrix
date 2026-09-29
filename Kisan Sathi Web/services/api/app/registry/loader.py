from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class RegistryError(ValueError):
    """Raised when the standalone tool contract is invalid or too large."""


_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_ALLOWED_KEYS = {
    "name",
    "description",
    "access",
    "annotations",
    "capabilities",
    "input_schema",
}


class ToolRegistry:
    def __init__(self, tools: list[dict[str, Any]], *, schema_version: int = 1) -> None:
        self.schema_version = schema_version
        self._tools = tuple(tools)
        self._by_name = {tool["name"]: tool for tool in tools}

    @classmethod
    def from_json(cls, path: Path, *, max_tools: int = 78) -> "ToolRegistry":
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RegistryError("Tool contract is unavailable or invalid.") from exc
        if not isinstance(document, dict) or not isinstance(document.get("tools"), list):
            raise RegistryError("Tool contract must contain a tools array.")
        if len(document["tools"]) > max_tools:
            raise RegistryError("Tool contract exceeds the configured tool bound.")
        tools: list[dict[str, Any]] = []
        names: set[str] = set()
        for raw in document["tools"]:
            if not isinstance(raw, dict) or not _ALLOWED_KEYS.issuperset(raw):
                raise RegistryError("Tool contract contains unsupported metadata.")
            name = raw.get("name")
            description = raw.get("description")
            if not isinstance(name, str) or not _NAME.fullmatch(name):
                raise RegistryError("Tool contract contains an invalid tool name.")
            if name in names:
                raise RegistryError("Tool contract contains duplicate tool names.")
            if not isinstance(description, str) or not description.strip():
                raise RegistryError("Tool descriptions are required.")
            if raw.get("access") not in {"read", "write"}:
                raise RegistryError("Tool access must be read or write.")
            if not isinstance(raw.get("input_schema"), dict):
                raise RegistryError("Tool input schemas are required.")
            names.add(name)
            tools.append({key: raw[key] for key in _ALLOWED_KEYS if key in raw})
        return cls(tools, schema_version=int(document.get("schema_version", 1)))

    def all(self) -> list[dict[str, Any]]:
        return [dict(tool) for tool in self._tools]

    def select(self, names: list[str] | None, *, max_tools: int) -> list[dict[str, Any]]:
        if names is None:
            selected = list(self._tools)
        else:
            selected = []
            for name in names:
                tool = self._by_name.get(name)
                if tool is not None and tool not in selected:
                    selected.append(tool)
        return [dict(tool) for tool in selected[:max_tools]]

    def __len__(self) -> int:
        return len(self._tools)

