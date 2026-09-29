from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/auth"))
sys.path.insert(0, str(ROOT / "packages/tool-registry"))


def test_canonical_registry_matches_frozen_contract():
    from registry import TOOL_REGISTRY

    baseline = json.loads((ROOT / "packages/contracts/tool-registry-baseline.json").read_text(encoding="utf-8"))
    expected = {item["name"] for item in baseline["tools"]}
    actual = {item.name for item in TOOL_REGISTRY}
    assert actual == expected
    assert len(actual) == 78
