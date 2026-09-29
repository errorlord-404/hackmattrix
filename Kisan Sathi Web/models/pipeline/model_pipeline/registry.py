"""Read-only backbone and recipe registry.

Importing this module never imports an ML framework and never activates a model.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .contracts import PipelineError, load_json, validate_schema


PIPELINE_ROOT = Path(__file__).resolve().parents[1]


class ModelRegistry:
    def __init__(self, root: Path = PIPELINE_ROOT):
        self.root = Path(root).resolve()

    def _validated(self, document_name: str, schema_name: str, label: str) -> dict[str, Any]:
        document = load_json(self.root / document_name, label)
        schema = load_json(self.root / schema_name, f"{label} schema")
        validate_schema(document, schema, label)
        return document

    def backbones(self) -> list[dict[str, Any]]:
        document = self._validated("backbones.json", "backbones.schema.json", "backbone registry")
        entries = document["backbones"]
        identifiers = [entry["backbone_id"] for entry in entries]
        if len(identifiers) != len(set(identifiers)):
            raise PipelineError("backbone_id values must be unique")
        return entries

    def recipe_document(self, path: Path | None = None) -> dict[str, Any]:
        recipe_path = Path(path).resolve() if path else self.root / "recipes" / "top15.json"
        document = load_json(recipe_path, "recipe catalog")
        schema = load_json(self.root / "recipes.schema.json", "recipe schema")
        validate_schema(document, schema, "recipe catalog")
        defaults = document["defaults"]
        if defaults["status"] not in {"template", "candidate"}:
            raise PipelineError("recipe status must remain template or candidate")
        group_keys = defaults["split"]["group_keys"]
        if len(group_keys) != len(set(group_keys)):
            raise PipelineError("grouped split keys must be unique")
        expanded: list[dict[str, Any]] = []
        for item in document["recipes"]:
            recipe = copy.deepcopy(defaults)
            recipe.update(copy.deepcopy(item))
            expanded.append(recipe)
        document = {**document, "recipes": expanded}
        backbone_ids = {entry["backbone_id"] for entry in self.backbones()}
        recipe_ids: set[str] = set()
        crop_specialists: set[str] = set()
        routers = 0
        for recipe in document["recipes"]:
            recipe_id = recipe["recipe_id"]
            if recipe_id in recipe_ids:
                raise PipelineError(f"duplicate recipe_id: {recipe_id}")
            recipe_ids.add(recipe_id)
            if recipe["backbone_id"] not in backbone_ids:
                raise PipelineError(f"unknown backbone_id in {recipe_id}: {recipe['backbone_id']}")
            labels = recipe["labels"]
            if len(labels) != len(set(labels)) or "unknown" not in labels:
                raise PipelineError(f"{recipe_id} labels must be unique and include unknown")
            if recipe["role"] == "crop_identifier":
                routers += 1
                if recipe["crop_id"] != "multi_crop":
                    raise PipelineError("crop identifier must use crop_id=multi_crop")
                if recipe["task"] != "crop_identification":
                    raise PipelineError("crop identifier must use crop_identification task")
            else:
                crop = recipe["crop_id"]
                if recipe["task"] != "crop_disease_screening":
                    raise PipelineError(
                        f"specialist {crop} must use crop_disease_screening task"
                    )
                if crop in crop_specialists:
                    raise PipelineError(f"duplicate specialist recipe for crop: {crop}")
                crop_specialists.add(crop)
                if "healthy" not in labels:
                    raise PipelineError(f"specialist {crop} must include healthy")
        if routers != 1:
            raise PipelineError("recipe catalog must contain exactly one crop identifier")
        declared = set(document["coverage"]["crop_ids"])
        if crop_specialists != declared:
            raise PipelineError(
                f"specialist coverage mismatch: missing={sorted(declared-crop_specialists)}, "
                f"extra={sorted(crop_specialists-declared)}"
            )
        router = next(item for item in document["recipes"] if item["role"] == "crop_identifier")
        if set(router["labels"]) != declared | {"unknown"}:
            raise PipelineError("router labels must equal crop coverage plus unknown")
        return document

    def recipes(self, path: Path | None = None) -> list[dict[str, Any]]:
        return self.recipe_document(path)["recipes"]

    def find_backbone(self, backbone_id: str) -> dict[str, Any]:
        for entry in self.backbones():
            if entry["backbone_id"] == backbone_id:
                return entry
        raise PipelineError(f"unknown backbone: {backbone_id}")

    def find_recipe(self, recipe_id: str, path: Path | None = None) -> dict[str, Any]:
        for recipe in self.recipes(path):
            if recipe["recipe_id"] == recipe_id:
                return recipe
        raise PipelineError(f"unknown recipe: {recipe_id}")

    def report(self) -> dict[str, Any]:
        backbones = self.backbones()
        document = self.recipe_document()
        return {
            "status": "templates_only",
            "activation_allowed": False,
            "backbone_count": len(backbones),
            "frameworks": sorted({item["framework"] for item in backbones}),
            "recipe_count": len(document["recipes"]),
            "crop_count": len(document["coverage"]["crop_ids"]),
        }
