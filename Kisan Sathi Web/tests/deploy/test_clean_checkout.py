from __future__ import annotations

from pathlib import Path

import pytest

from deploy.health.check import validate_compose


ROOT = Path(__file__).resolve().parents[2]


def test_clean_checkout_has_health_gated_three_service_topology():
    payload = validate_compose(ROOT / "deploy" / "compose.yaml")
    assert set(payload["services"]) >= {"api", "harness", "web"}
    assert payload["services"]["web"]["depends_on"]["harness"]["condition"] == "service_healthy"


def test_start_scripts_use_standalone_compose_only():
    for path in (ROOT / "scripts" / "start.ps1", ROOT / "scripts" / "start.sh"):
        text = path.read_text(encoding="utf-8")
        assert "deploy/compose.yaml" in text or "deploy\\compose.yaml" in text
        assert "..\\backend" not in text and "../backend" not in text


def test_prototype_overlay_binds_only_verified_research_models():
    overlay = ROOT / "deploy" / "compose.prototype.yaml"
    text = overlay.read_text(encoding="utf-8")
    assert "models/candidates/mesabo-agri-plant-disease-resnet50-61aa6c3" in text
    assert "read_only: true" in text
    assert "KISANSATHI_PROTOTYPE_MODE: \"true\"" in text
    assert "CROP_DISEASE_RESEARCH_MODE: \"true\"" in text
    assert "models/placeholders" not in text
    assert "Dockerfile.api.prototype" in text


def test_prototype_api_image_is_explicitly_separate_from_production_image():
    path = ROOT / "deploy" / "Dockerfile.api.prototype"
    text = path.read_text(encoding="utf-8")
    assert "onnxruntime" in text
    assert "USER kisansathi" in text
    assert "production Dockerfile" in text


def test_prototype_start_scripts_use_the_overlay():
    for path in (ROOT / "scripts" / "start-prototype.ps1", ROOT / "scripts" / "start-prototype.sh"):
        text = path.read_text(encoding="utf-8")
        assert "compose.prototype.yaml" in text
        assert "validate_prototype_models.py" in text


@pytest.mark.parametrize("path", [ROOT / "deploy" / "Dockerfile.api", ROOT / "deploy" / "Dockerfile.harness"])
def test_service_images_use_least_privilege_user(path: Path):
    assert "USER kisansathi" in path.read_text(encoding="utf-8")
