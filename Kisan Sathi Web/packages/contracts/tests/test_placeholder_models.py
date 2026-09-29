import json
import shutil
import sys
from pathlib import Path

import pytest

TARGET = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TARGET / "scripts"))
from validate_placeholder_models import PlaceholderError, validate_placeholders  # noqa: E402


INDEX = TARGET / "models" / "placeholders" / "index.json"


def test_real_placeholder_is_installed_but_never_approved() -> None:
    report = validate_placeholders(INDEX, require_installed=True)
    assert report == {
        "package_count": 16,
        "installed_count": 16,
        "research_checkpoint_count": 1,
        "structural_stub_count": 15,
        "crop_slot_count": 15,
        "status": "research_placeholders_only",
    }
    manifest = json.loads((INDEX.parent / "ktt-mobilenetv3-int8" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "research_placeholder_unapproved"
    assert manifest["enabled"] is False
    assert manifest["approval"]["release_approved"] is False


def test_top_15_structural_stubs_are_non_diagnostic_and_disabled() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    stubs = [package for package in index["packages"] if package["kind"] == "structural_stub"]
    assert len(stubs) == 15
    assert len({package["crop_id"] for package in stubs}) == 15
    for package in stubs:
        manifest = json.loads((INDEX.parent / package["manifest"]).read_text(encoding="utf-8"))
        assert manifest["status"] == "structural_stub_untrained"
        assert manifest["enabled"] is False
        assert manifest["diagnostic_capability"] is False
        assert manifest["approval"]["release_approved"] is False
        assert manifest["approval"]["activation_prohibited"] is True
        assert manifest["model_contract"]["behavior"] == "constant_zero_logits_non_diagnostic"


def test_top_15_slots_match_the_production_catalog_without_becoming_releases() -> None:
    coverage = json.loads((INDEX.parent / "top-15-india.json").read_text(encoding="utf-8"))
    catalog = json.loads((TARGET / "models" / "catalog.json").read_text(encoding="utf-8"))
    crop_ids = {crop["crop_id"] for crop in coverage["crops"]}
    specialists = {entry["crop"]: entry for entry in catalog["models"] if entry["role"] == "disease_specialist"}
    assert len(crop_ids) == 15
    assert crop_ids <= specialists.keys()
    for crop_id in crop_ids:
        assert specialists[crop_id]["artifacts"]["model"]["path"] is None
        assert specialists[crop_id]["status"] != "approved"


def test_placeholder_hash_tampering_fails_closed(tmp_path: Path) -> None:
    copied = tmp_path / "placeholders"
    shutil.copytree(INDEX.parent, copied)
    model = copied / "ktt-mobilenetv3-int8" / "model.onnx"
    model.write_bytes(model.read_bytes() + b"tampered")
    with pytest.raises(PlaceholderError, match="size mismatch|SHA-256 mismatch"):
        validate_placeholders(copied / "index.json", require_installed=True)


def test_placeholder_cannot_be_enabled_by_manifest_edit(tmp_path: Path) -> None:
    copied = tmp_path / "placeholders"
    shutil.copytree(INDEX.parent, copied)
    manifest_path = copied / "ktt-mobilenetv3-int8" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["enabled"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PlaceholderError, match="must be disabled"):
        validate_placeholders(copied / "index.json", require_installed=True)
