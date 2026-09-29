from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

from model_pipeline.contracts import PipelineError
from model_pipeline.registry import ModelRegistry


def test_top15_router_and_specialists_are_uniform() -> None:
    recipes = ModelRegistry().recipes()
    router = [item for item in recipes if item["role"] == "crop_identifier"]
    specialists = [item for item in recipes if item["role"] == "disease_specialist"]
    assert len(router) == 1
    assert len(specialists) == 15
    assert len(router[0]["labels"]) == 16
    assert router[0]["labels"][-1] == "unknown"
    assert all(item["labels"][0] == "healthy" and item["labels"][-1] == "unknown" for item in specialists)
    assert all(item["quantization"]["default"] == "static-int8" for item in recipes)
    assert all(item["status"] == "template" for item in recipes)
    assert all("preprocessing" in item and "training" in item for item in recipes)
    assert all(item["split"]["group_keys"] for item in recipes)
    assert all(item["seed"] >= 0 for item in recipes)
    assert all(item["evaluation"]["thresholds"]["min_macro_f1"] > 0 for item in recipes)


def test_recipes_are_generated_from_top15_crop_contract() -> None:
    source_path = PIPELINE_ROOT.parent / "placeholders" / "top-15-india.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    recipes = ModelRegistry().recipes()
    router = next(item for item in recipes if item["role"] == "crop_identifier")
    specialists = {
        item["crop_id"]: item
        for item in recipes
        if item["role"] == "disease_specialist"
    }
    crop_ids = [crop["crop_id"] for crop in source["crops"]]
    assert router["labels"] == crop_ids + ["unknown"]
    assert set(specialists) == set(crop_ids)
    for crop in source["crops"]:
        assert specialists[crop["crop_id"]]["labels"] == crop["classes"] + ["unknown"]


def test_recipe_without_unknown_is_rejected(tmp_path: Path) -> None:
    source = PIPELINE_ROOT / "recipes" / "top15.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["recipes"][0]["labels"].remove("unknown")
    candidate = tmp_path / "recipes.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PipelineError, match="include unknown|coverage plus unknown"):
        ModelRegistry().recipe_document(candidate)
