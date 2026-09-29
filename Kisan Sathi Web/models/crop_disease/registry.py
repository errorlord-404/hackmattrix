"""Machine-readable specialist registry; no crop/model mappings live in code."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .ontology import CANONICAL_CROPS, normalize_crop


class RegistryError(ValueError):
    pass


STATUSES = {"VERIFIED_DOWNLOADABLE", "HOSTED_ONLY", "PAPER_NO_WEIGHTS", "NOT_AVAILABLE", "CUSTOM_FUTURE_MODEL"}


@dataclass(frozen=True, slots=True)
class ModelEntry:
    id: str
    name: str
    status: str
    provider: str
    framework: str
    architecture: str
    task: str
    crops: tuple[str, ...]
    source_url: str
    remote_id: str | None
    local_path: str
    license: str
    training_domain: str
    priority: int
    enabled: bool
    revision: str | None
    input_size: int
    class_mapping: str | None
    preprocessing: dict[str, Any]
    notes: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ModelEntry":
        required = ("id", "name", "status", "provider", "framework", "architecture", "task", "crops", "source_url", "local_path", "license", "training_domain", "priority", "enabled", "preprocessing")
        missing = [key for key in required if key not in raw]
        if missing:
            raise RegistryError(f"model entry missing fields: {missing}")
        if raw["status"] not in STATUSES:
            raise RegistryError(f"invalid model status: {raw['status']}")
        crops = tuple(raw["crops"])
        if not crops or any(crop not in CANONICAL_CROPS for crop in crops):
            raise RegistryError(f"model {raw['id']} has invalid supported crops")
        return cls(
            id=str(raw["id"]), name=str(raw["name"]), status=str(raw["status"]), provider=str(raw["provider"]),
            framework=str(raw["framework"]), architecture=str(raw["architecture"]), task=str(raw["task"]),
            crops=crops, source_url=str(raw["source_url"]), remote_id=raw.get("remote_id"), local_path=str(raw["local_path"]),
            license=str(raw["license"]), training_domain=str(raw["training_domain"]), priority=int(raw["priority"]),
            enabled=bool(raw["enabled"]), revision=raw.get("revision"), input_size=int(raw.get("input_size", 224)),
            class_mapping=raw.get("class_mapping"), preprocessing=dict(raw["preprocessing"]), notes=str(raw.get("notes", "")),
        )


class CropDiseaseRegistry:
    def __init__(self, entries: Iterable[ModelEntry], source_path: Path):
        self.source_path = source_path
        self.entries = tuple(entries)
        ids = [item.id for item in self.entries]
        if len(ids) != len(set(ids)):
            raise RegistryError("duplicate model IDs")

    @classmethod
    def from_path(cls, path: Path) -> "CropDiseaseRegistry":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"unable to read crop disease registry: {exc}") from exc
        if raw.get("schema_version") != "1.0" or not isinstance(raw.get("models"), list):
            raise RegistryError("invalid crop disease registry")
        return cls((ModelEntry.from_dict(item) for item in raw["models"]), path.resolve())

    def get(self, model_id: str) -> ModelEntry:
        for entry in self.entries:
            if entry.id == model_id:
                return entry
        raise RegistryError(f"unknown model: {model_id}")

    def candidates(self, crop: str, *, executable_only: bool = False) -> list[ModelEntry]:
        normalized = normalize_crop(crop)
        if not normalized:
            return []
        items = [item for item in self.entries if normalized in item.crops and item.enabled]
        if executable_only:
            items = [item for item in items if item.status == "VERIFIED_DOWNLOADABLE"]
        return sorted(items, key=lambda item: (-item.priority, item.id))

    def coverage(self, downloaded_root: Path | None = None) -> dict[str, dict[str, Any]]:
        root = downloaded_root.resolve() if downloaded_root else None
        result: dict[str, dict[str, Any]] = {}
        for crop in CANONICAL_CROPS:
            models = self.candidates(crop)
            result[crop] = {
                "specialist_available": any(item.status == "VERIFIED_DOWNLOADABLE" for item in models),
                "models": [self.public_entry(item, root) for item in models],
            }
        return result

    @staticmethod
    def public_entry(entry: ModelEntry, downloaded_root: Path | None = None) -> dict[str, Any]:
        local = downloaded_root / entry.local_path if downloaded_root else None
        return {
            "id": entry.id, "name": entry.name, "status": entry.status, "downloaded": bool(local and local.is_dir()),
            "loadable": False, "crops": list(entry.crops), "framework": entry.framework, "architecture": entry.architecture,
            "license": entry.license, "training_domain": entry.training_domain, "priority": entry.priority, "enabled": entry.enabled,
            "source_url": entry.source_url, "revision": entry.revision, "notes": entry.notes,
        }


def default_registry_path() -> Path:
    return Path(__file__).resolve().with_name("registry.json")

