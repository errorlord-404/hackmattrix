from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_api_and_harness_composition_roots_are_standalone():
    api = (ROOT / "services/api/app/main.py").read_text(encoding="utf-8")
    harness = (ROOT / "services/harness/app/main.py").read_text(encoding="utf-8")
    for marker in ("domain_router", "reference_router", "vision_router", "media_router", "crop_disease_router"):
        assert marker in api
    for marker in ("/sessions", "/capabilities", "/readyz", "text/event-stream"):
        assert marker in harness


def test_frontend_parity_baseline_has_a_standalone_owner_for_every_row():
    baseline = json.loads((ROOT / "packages/contracts/frontend-parity-baseline.json").read_text(encoding="utf-8"))
    assert len(baseline["workflows"]) == 20
    for workflow in baseline["workflows"]:
        owner = ROOT / workflow["standalone_feature_owner"]
        assert owner.exists(), workflow["id"]
        assert workflow["final_black_box_test_id"]
