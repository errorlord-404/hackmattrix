from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_prototype_status_exposes_verified_research_models_without_production_approval(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/crop-disease/prototype")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prototype_only"] is True
    assert payload["production_approved"] is False
    assert payload["activation_allowed"] is False
    assert payload["diagnostic_use_allowed"] is False
    assert "tomato" in {item["id"] for item in payload["supported_crops"]}


def test_prototype_model_route_requires_verified_installed_model(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/v1/crop-disease/models/mesabo_resnet50")

    assert response.status_code == 200
    assert response.json()["status"] == "VERIFIED_DOWNLOADABLE"
