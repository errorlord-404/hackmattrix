from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.model_catalog import CropCandidate, HierarchicalModelCatalog
from app.settings import ServiceSettings


ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "models" / "catalog.json"


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _approve(entry: dict) -> None:
    entry["status"] = "approved"
    entry["version"] = "1.0.0"
    entry["research"]["readiness"] = "release_evidence"
    entry["research"]["field_evidence"] = "passed"
    entry["artifacts"] = {
        "release_manifest": f"releases/{entry['model_id']}/manifest.json",
        "model": {"path": f"releases/{entry['model_id']}/model.onnx", "sha256": "a" * 64, "size_bytes": 1024},
        "labels": {"path": f"releases/{entry['model_id']}/labels.json", "sha256": "b" * 64, "size_bytes": 128},
    }


def test_capabilities_expose_coverage_but_no_loadable_research_artifacts(settings: ServiceSettings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/v1/vision/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["architecture"] == "crop_identifier_then_crop_specialist"
    assert body["mode"] == "scaffold"
    assert body["coverage_count"] == 26
    assert body["approved_specialist_count"] == 0
    assert all(not crop["client_eligible"] for crop in body["crops"])
    assert "path" not in response.text
    assert "sha256" not in response.text


def test_unapproved_identifier_requires_farmer_confirmation() -> None:
    catalog = HierarchicalModelCatalog(_catalog())
    decision = catalog.select_specialist([CropCandidate("tomato", 0.99)])
    assert decision.status == "needs_crop_confirmation"
    assert decision.requires_farmer_confirmation is True
    assert decision.specialist_id is None


def test_farmer_confirmation_still_fails_closed_without_approved_specialist() -> None:
    catalog = HierarchicalModelCatalog(_catalog())
    decision = catalog.select_specialist([], confirmed_crop="rice")
    assert decision.status == "needs_expert_review"
    assert decision.crop == "rice"


def test_approved_identifier_routes_only_to_approved_lazy_specialist() -> None:
    document = copy.deepcopy(_catalog())
    identifier = next(entry for entry in document["models"] if entry["role"] == "crop_identifier")
    tomato = next(entry for entry in document["models"] if entry["crop"] == "tomato")
    _approve(identifier)
    _approve(tomato)
    catalog = HierarchicalModelCatalog(document)

    routed = catalog.select_specialist([CropCandidate("tomato", 0.94), CropCandidate("potato", 0.04)])
    unavailable = catalog.select_specialist([CropCandidate("potato", 0.94), CropCandidate("tomato", 0.04)])

    assert routed.status == "routed"
    assert routed.specialist_id == "disease-tomato"
    assert unavailable.status == "needs_expert_review"
    assert unavailable.specialist_id is None


def test_ambiguous_identifier_never_selects_a_specialist() -> None:
    document = copy.deepcopy(_catalog())
    identifier = next(entry for entry in document["models"] if entry["role"] == "crop_identifier")
    tomato = next(entry for entry in document["models"] if entry["crop"] == "tomato")
    _approve(identifier)
    _approve(tomato)
    catalog = HierarchicalModelCatalog(document)

    decision = catalog.select_specialist([CropCandidate("tomato", 0.80), CropCandidate("potato", 0.74)])
    assert decision.status == "needs_crop_confirmation"
    assert decision.specialist_id is None
