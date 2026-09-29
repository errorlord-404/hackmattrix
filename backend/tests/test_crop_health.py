from hashlib import sha256
from pathlib import Path

from app.services import crop_health
from app.services import tflite_crop_health


def test_local_crop_health_requires_explicit_provider(monkeypatch, tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"not-used-when-disabled")
    monkeypatch.setattr(crop_health.settings, "DIAGNOSIS_PROVIDER", "unconfigured")
    response = crop_health.diagnose_image(image, "tomato")
    assert response["status"] == "provider_unavailable"
    assert response["crop"] == "tomato"
    assert response.get("label") is None


def test_local_crop_health_never_routes_unknown_crop(monkeypatch, tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"not-used-before-runtime")
    monkeypatch.setattr(crop_health.settings, "DIAGNOSIS_PROVIDER", "local_hierarchical_demo")
    monkeypatch.setattr(crop_health.settings, "CROP_HEALTH_ROUTER_MODEL_PATH", str(tmp_path / "router.pt"))
    response = crop_health.diagnose_image(image, "I do not know")
    assert response["status"] == "needs_crop_confirmation"
    assert response.get("label") is None


def test_tflite_candidate_gate_requires_score_and_clear_margin(monkeypatch):
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_MIN_DISEASE_SCORE", 0.70)
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_MIN_DISEASE_MARGIN", 0.15)
    assert tflite_crop_health._review_reason([{"label": "healthy", "score": 0.68}])
    assert tflite_crop_health._review_reason([
        {"label": "healthy", "score": 0.82}, {"label": "late_blight", "score": 0.75},
    ])
    assert tflite_crop_health._review_reason([
        {"label": "healthy", "score": 0.90}, {"label": "late_blight", "score": 0.60},
    ]) is None


def test_tflite_crop_router_gate_is_conservative(monkeypatch):
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_MIN_CROP_SCORE", 0.80)
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_MIN_CROP_MARGIN", 0.15)
    assert tflite_crop_health._crop_review_reason([{"label": "tomato", "score": 0.79}])
    assert tflite_crop_health._crop_review_reason([
        {"label": "tomato", "score": 0.91}, {"label": "potato", "score": 0.80},
    ])
    assert tflite_crop_health._crop_review_reason([
        {"label": "tomato", "score": 0.93}, {"label": "potato", "score": 0.60},
    ]) is None


def test_unknown_tflite_crop_enters_confirmation_route(monkeypatch, tmp_path):
    from PIL import Image, ImageDraw

    image = tmp_path / "leaf.jpg"
    fixture = Image.new("RGB", (200, 200), color=(120, 160, 80))
    ImageDraw.Draw(fixture).ellipse((35, 25, 165, 180), fill=(25, 95, 30))
    fixture.save(image)
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_ROUTER_MODEL_PATH", "")
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_ROUTER_LABELS_PATH", "")
    response = tflite_crop_health.run_tflite_specialist(image, "I do not know")
    assert response["status"] == "needs_crop_confirmation"
    assert response["crop"] is None


def test_controlled_tflite_candidate_never_becomes_completed_without_release_manifest(monkeypatch, tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"fixture")
    model, labels = tmp_path / "model.tflite", tmp_path / "labels.json"
    model.write_bytes(b"fixture"); labels.write_text('["healthy", "late_blight"]')
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_MODEL_PATH", str(model))
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_LABELS_PATH", str(labels))
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_CROP", "tomato")
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH", "")
    monkeypatch.setattr(tflite_crop_health, "_quality_issue", lambda _: None)
    monkeypatch.setattr(tflite_crop_health, "_tflite_candidates", lambda *_: [{"label": "healthy", "score": 0.95}, {"label": "late_blight", "score": 0.02}])
    response = tflite_crop_health.run_tflite_specialist(image, "tomato")
    assert response["status"] == "needs_expert_review"
    assert response["disease_candidates"][0]["label"] == "healthy"
    assert response.get("label") is None


def test_tflite_completed_result_requires_matching_passed_release_manifest(monkeypatch, tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"fixture")
    model, labels = tmp_path / "model.tflite", tmp_path / "labels.json"
    model.write_bytes(b"model-artifact")
    labels.write_text('["healthy", "late_blight"]', encoding="utf-8")
    manifest = tmp_path / "approved-release.yaml"
    manifest.write_text(
        "\n".join(
            [
                "release_id: tomato-field-v1",
                "status: approved_for_field_release",
                "supported_crop: tomato",
                "artifact:",
                f"  sha256: {sha256(model.read_bytes()).hexdigest()}",
                "labels:",
                f"  sha256: {sha256(labels.read_bytes()).hexdigest()}",
                "release_gates:",
                "  independent_field_test: passed",
                "  unknown_ood_test: passed",
                "  agronomist_review: passed",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_MODEL_PATH", str(model))
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_LABELS_PATH", str(labels))
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_CROP", "tomato")
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(tflite_crop_health, "_quality_issue", lambda _: None)
    monkeypatch.setattr(tflite_crop_health, "_tflite_candidates", lambda *_: [{"label": "healthy", "score": 0.95}, {"label": "late_blight", "score": 0.02}])
    response = tflite_crop_health.run_tflite_specialist(image, "tomato")
    assert response["status"] == "completed"
    assert response["label"] == "healthy"


def test_tflite_release_manifest_rejects_artifact_checksum_mismatch(monkeypatch, tmp_path):
    model, labels = tmp_path / "model.tflite", tmp_path / "labels.json"
    model.write_bytes(b"model-artifact")
    labels.write_text('["healthy"]', encoding="utf-8")
    manifest = tmp_path / "bad-release.yaml"
    manifest.write_text(
        """status: approved_for_field_release
supported_crop: tomato
artifact: {sha256: mismatch}
labels: {sha256: mismatch}
release_gates: {independent_field_test: passed, unknown_ood_test: passed, agronomist_review: passed}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH", str(manifest))
    assert "checksum" in tflite_crop_health._release_approval_reason(model, labels, "tomato")


def test_tflite_model_identity_comes_from_the_configured_manifest(monkeypatch, tmp_path):
    manifest = tmp_path / "controlled-demo.yaml"
    manifest.write_text(
        "\n".join(
            [
                "release_id: crop-health-controlled-v3",
                "status: demo_only_rejected_for_field_release",
                "runtime:",
                "  source_backbone: tfhub/google/efficientnet_v2_b0",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tflite_crop_health.settings, "CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH", str(manifest))
    assert tflite_crop_health._configured_model_identity() == (
        "tfhub/google/efficientnet_v2_b0",
        "crop-health-controlled-v3",
    )
