from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from registry import (  # noqa: E402
    FORBIDDEN_ARGUMENT_NAMES,
    TOOL_REGISTRY,
    get_tool,
    model_visible_tools,
    registry_snapshot,
)


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def test_registry_is_exact_frozen_78_tool_contract() -> None:
    baseline = json.loads((PACKAGE.parent / "contracts" / "tool-registry-baseline.json").read_text(encoding="utf-8"))
    assert registry_snapshot() == baseline
    assert len(TOOL_REGISTRY) == 78
    assert sum(tool.read_only for tool in TOOL_REGISTRY) == 56
    assert sum(not tool.read_only for tool in TOOL_REGISTRY) == 22
    assert len({tool.name for tool in TOOL_REGISTRY}) == 78


def test_model_schemas_exclude_identity_secrets_paths_and_controls() -> None:
    for tool in TOOL_REGISTRY:
        keys = {key.casefold() for key in _walk_keys(tool.input_schema)}
        assert not keys & FORBIDDEN_ARGUMENT_NAMES, tool.name
        assert tool.input_schema.get("additionalProperties") is False
    assert model_visible_tools() == []
    assert model_visible_tools(["list_fields"])[0]["name"] == "list_fields"
    with pytest.raises(Exception):
        model_visible_tools(["missing_tool"])


def test_metadata_keeps_external_compute_distinct_from_persistence() -> None:
    assert get_tool("diagnose_crop").effect_class == "external_compute"
    assert get_tool("diagnose_crop").confirmation_required is False
    assert get_tool("create_field").effect_class == "authoritative_persistence"
    assert get_tool("create_field").confirmation_required is True
    assert get_tool("calculate_profit").effect_class == "external_compute"
