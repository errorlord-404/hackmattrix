import json
import sys
from pathlib import Path

import pytest

TARGET = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TARGET / "scripts"))
from validate_model_catalog import CatalogError, validate_catalog  # noqa: E402


CATALOG = TARGET / "models" / "catalog.json"


def test_scaffold_catalog_is_valid_but_not_deployable() -> None:
    report = validate_catalog(CATALOG)
    assert report["model_count"] == 27
    assert report["coverage_count"] == 26
    assert report["research_source_count"] == 9
    assert report["approved_count"] == 0
    assert report["approved_identifier"] is False


def test_require_approved_fails_closed_for_placeholder() -> None:
    with pytest.raises(CatalogError, match="no approved crop identifier"):
        validate_catalog(CATALOG, require_approved=True)


def test_missing_entry_cannot_claim_partial_artifact(tmp_path: Path) -> None:
    schema = json.loads((TARGET / "models" / "catalog.schema.json").read_text(encoding="utf-8"))
    (tmp_path / "catalog.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    source_schema = json.loads((TARGET / "models" / "research-sources.schema.json").read_text(encoding="utf-8"))
    sources = json.loads((TARGET / "models" / "research-sources.json").read_text(encoding="utf-8"))
    (tmp_path / "research-sources.schema.json").write_text(json.dumps(source_schema), encoding="utf-8")
    (tmp_path / "research-sources.json").write_text(json.dumps(sources), encoding="utf-8")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog["models"][0]["artifacts"]["model"]["path"] = "releases/tomato/model.onnx"
    (tmp_path / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(CatalogError, match="non-approved"):
        validate_catalog(tmp_path / "catalog.json")


def test_every_common_crop_has_exactly_one_modular_specialist_slot() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    specialists = [entry for entry in catalog["models"] if entry["role"] == "disease_specialist"]
    assert sorted(entry["crop"] for entry in specialists) == sorted(catalog["coverage"]["crop_ids"])
    assert all(entry["runtime"]["lazy_load"] is True for entry in specialists)
    assert all(entry["artifacts"]["model"]["path"] is None for entry in specialists)


def test_research_candidates_are_not_executable_releases() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    candidates = [entry for entry in catalog["models"] if entry["status"] == "research_candidate"]
    assert {entry["crop"] for entry in candidates} >= {"multi_crop", "rice", "wheat", "maize", "tomato"}
    assert all(entry["research"]["readiness"] != "release_evidence" for entry in candidates)
    assert all(entry["artifacts"]["release_manifest"] is None for entry in candidates)


def test_chilli_is_not_silently_mapped_to_bell_pepper_data() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    chilli = next(entry for entry in catalog["models"] if entry["crop"] == "chilli")
    assert chilli["status"] == "missing"
    assert "plantvillage" not in chilli["research"]["source_ids"]
