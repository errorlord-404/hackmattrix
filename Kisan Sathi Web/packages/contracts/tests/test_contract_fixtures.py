from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


TARGET = Path(__file__).resolve().parents[3]
REPO = TARGET.parent
MANIFEST = TARGET / "docs" / "MIGRATION_MANIFEST.md"


def load_script(name: str):
    path = TARGET / "scripts" / f"{name}.py"
    assert path.is_file(), f"missing standalone script: {path}"
    spec = importlib.util.spec_from_file_location(f"standalone_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_manifest_has_required_columns_and_dispositions() -> None:
    assert MANIFEST.is_file()
    module = load_script("capture_parent_baseline")
    entries = module.parse_manifest(MANIFEST)
    assert entries
    assert {entry.disposition for entry in entries} <= {"copy", "adapt", "replace", "exclude"}
    for entry in entries:
        assert entry.source and entry.target and entry.rationale
        assert entry.source_sha256 or entry.disposition == "exclude"
    module.validate_manifest(entries, REPO, TARGET)


def test_manifest_covers_required_categories_and_exclusions() -> None:
    module = load_script("capture_parent_baseline")
    entries = module.parse_manifest(MANIFEST)
    sources = "\n".join(entry.source for entry in entries)
    targets = "\n".join(entry.target for entry in entries)
    for marker in (
        "src/App.jsx",
        "backend/app/main.py",
        "agent/src/kisansathi_agent/server.py",
        "desktop/codex-harness.cjs",
        "ml/contracts/crop-health-result.schema.json",
        "scripts/check_api_contracts.py",
    ):
        assert marker in sources
    for marker in ("node_modules", "dist", ".git", "codex", "*.sqlite*", "secrets"):
        assert marker in sources or marker in targets
    assert any(entry.disposition == "replace" for entry in entries)
    assert any(entry.disposition == "exclude" for entry in entries)


def test_manifest_rejects_unsafe_rows() -> None:
    module = load_script("capture_parent_baseline")
    unsafe = """# Manifest\n\n| Source | Target | Disposition | SHA-256 | Rationale |\n|---|---|---|---|---|\n| src/App.jsx | ../escape.jsx | copy | deadbeef | bad |\n"""
    path = TARGET / "docs" / "_unsafe_manifest_test.md"
    path.write_text(unsafe, encoding="utf-8")
    try:
        with pytest.raises(module.ManifestError):
            module.validate_manifest(module.parse_manifest(path), REPO, TARGET)
    finally:
        path.unlink()


def test_parent_baseline_is_immutable_and_checks_parent_paths(tmp_path: Path) -> None:
    module = load_script("capture_parent_baseline")
    output = tmp_path / "baseline.json"
    first = module.capture_baseline(REPO, TARGET)
    module.write_baseline(output, first)
    assert first["head"]
    assert "porcelain_v2" in first
    assert first["capture_root"] == "."
    assert all(not path.startswith("Kisan Sathi Web/") for path in first["files"])
    with pytest.raises(module.BaselineExistsError):
        module.write_baseline(output, first)
    assert module.check_baseline(output, REPO, TARGET) is True


def test_parent_baseline_detects_changed_file(tmp_path: Path) -> None:
    module = load_script("capture_parent_baseline")
    output = tmp_path / "baseline.json"
    snapshot = module.capture_baseline(REPO, TARGET)
    module.write_baseline(output, snapshot)
    changed = dict(snapshot)
    changed["files"] = dict(snapshot["files"])
    changed["files"]["synthetic-parent-file.txt"] = "0" * 64
    output.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")
    assert module.check_baseline(output, REPO, TARGET) is False


def test_frontend_parity_baseline_has_one_owner_per_visible_workflow() -> None:
    path = TARGET / "packages" / "contracts" / "frontend-parity-baseline.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["workflows"]
    assert len(rows) >= 20
    for row in rows:
        for key in (
            "id", "route", "workflow", "baseline_source", "visible_states", "input",
            "output", "safety_boundary", "frozen_contract_fixture", "standalone_feature_owner",
            "final_black_box_test_id",
        ):
            assert row.get(key)
        assert set(("success", "degraded", "empty", "error")) <= set(row["visible_states"])
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["final_black_box_test_id"] for row in rows}) == len(rows)


def test_frontend_parity_validator_rejects_duplicate_test_owner() -> None:
    module = load_script("capture_parent_baseline")
    path = TARGET / "packages" / "contracts" / "frontend-parity-baseline.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["workflows"][1]["final_black_box_test_id"] = payload["workflows"][0]["final_black_box_test_id"]
    with pytest.raises(ValueError):
        module.validate_frontend_parity(payload)


def test_allowlisted_copy_dry_run_and_apply_are_exact(tmp_path: Path) -> None:
    module = load_script("copy_allowlisted")
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "src").mkdir(parents=True)
    (source / "src" / "one.txt").write_bytes(b"one\n")
    digest = hashlib.sha256((source / "src" / "one.txt").read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.md"
    manifest.write_text(
        "| Source | Target | Disposition | SHA-256 | Rationale |\n|---|---|---|---|---|\n"
        f"| src/one.txt | copied/one.txt | copy | {digest} | fixture |\n"
        "| src/ignored.txt | none | exclude | — | excluded |\n",
        encoding="utf-8",
    )
    entries = module.parse_manifest(manifest)
    dry_run = module.copy_entries(entries, source, target, dry_run=True)
    assert dry_run == [{"operation": "create", "target": "copied/one.txt"}]
    assert not target.exists()
    assert module.copy_entries(entries, source, target, dry_run=False) == dry_run
    assert (target / "copied" / "one.txt").read_text(encoding="utf-8") == "one\n"


def test_allowlisted_copy_rejects_source_drift_and_target_escape(tmp_path: Path) -> None:
    module = load_script("copy_allowlisted")
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "one.txt").write_text("changed", encoding="utf-8")
    entry = module.ManifestEntry("one.txt", "one.txt", "copy", "0" * 64, "test")
    with pytest.raises(module.CopySafetyError):
        module.copy_entries([entry], source, target, dry_run=True)
    unsafe = module.ManifestEntry("one.txt", "../escape.txt", "copy", hashlib.sha256(b"changed").hexdigest(), "test")
    with pytest.raises(module.CopySafetyError):
        module.copy_entries([unsafe], source, target, dry_run=True)


def test_exported_api_and_tool_baselines_have_exact_counts() -> None:
    openapi = json.loads((TARGET / "packages" / "contracts" / "openapi-baseline.json").read_text(encoding="utf-8"))
    tools = json.loads((TARGET / "packages" / "contracts" / "tool-registry-baseline.json").read_text(encoding="utf-8"))
    assert openapi["counts"] == {"openapi_path_shapes": 84, "frontend_used_path_shapes": 53}
    assert len(openapi["paths"]) == 84
    assert len(openapi["frontend_paths"]) == 53
    assert len(tools["tools"]) == 78
    assert tools["counts"] == {"read": 56, "write": 22}
    assert len({tool["name"] for tool in tools["tools"]}) == 78
    assert not {"farmer_id", "tenant_id", "api_key", "authorization"} & set(json.dumps(tools).lower().split('"'))


def test_export_check_is_deterministic_and_parent_safe() -> None:
    module = load_script("export_baseline")
    before = json.loads((TARGET / "packages" / "contracts" / "openapi-baseline.json").read_text(encoding="utf-8"))
    assert module.check_baselines(REPO, TARGET / "packages" / "contracts") is True
    assert before == json.loads((TARGET / "packages" / "contracts" / "openapi-baseline.json").read_text(encoding="utf-8"))


def test_boundary_scan_rejects_parent_imports_and_undeclared_files(tmp_path: Path) -> None:
    module = load_script("check_standalone_boundary")
    (tmp_path / "declared.py").write_text("from ..parent import secret\n", encoding="utf-8")
    problems = module.scan_boundary(tmp_path, declared={"declared.py"})
    assert any("parent-relative" in problem for problem in problems)
    (tmp_path / "undeclared.txt").write_text("runtime", encoding="utf-8")
    problems = module.scan_boundary(tmp_path, declared={"declared.py"})
    assert any("undeclared" in problem for problem in problems)


EVENT_GOLDENS = [
    {"version": "1.0", "event_id": "evt-ready-001", "session_id": "sess-001", "turn_id": "turn-001", "sequence": 1, "occurred_at": "2026-09-17T10:00:00Z", "kind": "ready", "payload": {"resumed": False}, "delivery": {"cursor": "1", "replay": False, "duplicate": False}},
    {"version": "1.0", "event_id": "evt-tool-002", "session_id": "sess-001", "turn_id": "turn-001", "sequence": 2, "occurred_at": "2026-09-17T10:00:01Z", "kind": "tool", "payload": {"tool": "get_profile", "status": "completed"}, "delivery": {"cursor": "2", "replay": True, "duplicate": False}},
    {"version": "1.0", "event_id": "evt-cancel-003", "session_id": "sess-001", "turn_id": "turn-001", "sequence": 3, "occurred_at": "2026-09-17T10:00:02Z", "kind": "cancelled", "payload": {"reason": "farmer_requested"}, "delivery": {"cursor": "3", "replay": False, "duplicate": True}},
]


TOOL_GOLDENS = [
    {"status": "ok", "summary": "Profile loaded", "data": {"name": "Asha"}, "source": "kisansathi_backend", "warnings": [], "request_id": "req-001", "freshness": {"observed_at": "2026-09-17T10:00:00Z", "fetched_at": "2026-09-17T10:00:01Z", "age_seconds": 1}, "bounds": {"max_bytes": 32768, "truncated": False}, "action": None},
    {"status": "degraded", "summary": "Weather provider unavailable", "data": {"provider": "weather"}, "source": "kisansathi_backend", "warnings": ["provider_unavailable"], "request_id": "req-002", "freshness": None, "bounds": {"max_bytes": 32768, "truncated": False}, "action": None},
    {"status": "ok", "summary": "Irrigation event recorded", "data": {"id": "irr-1"}, "source": "kisansathi_backend", "warnings": [], "request_id": "req-003", "freshness": None, "bounds": {"max_bytes": 32768, "truncated": False}, "action": {"method": "POST", "path": "/v1/irrigation-events", "resource_type": "irrigation_event", "affected_ids": {"id": "irr-1"}, "timestamp": "2026-09-17T10:00:01Z", "source": "kisansathi_backend", "warnings": [], "refresh": ["irrigation", "timeline", "dashboard"]}},
]


def _schema(name: str) -> dict:
    return json.loads((TARGET / "packages" / "contracts" / name).read_text(encoding="utf-8"))


def test_event_envelope_goldens_validate_and_identity_is_required() -> None:
    schema = _schema("events.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for golden in EVENT_GOLDENS:
        validator.validate(golden)
    invalid = dict(EVENT_GOLDENS[0])
    invalid.pop("event_id")
    with pytest.raises(Exception):
        validator.validate(invalid)


def test_tool_result_goldens_preserve_bounds_provenance_and_authoritative_action() -> None:
    schema = _schema("tool-result.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for golden in TOOL_GOLDENS:
        validator.validate(golden)
    invalid = dict(TOOL_GOLDENS[2])
    invalid["action"] = {"method": "POST"}
    with pytest.raises(Exception):
        validator.validate(invalid)


def test_provider_capability_contract_requires_declared_limits_and_cancellation() -> None:
    schema = _schema("provider-capabilities.schema.json")
    validator = Draft202012Validator(schema)
    validator.validate({"version": "1.0", "provider": "fake", "capabilities": {"text_input": True, "image_input": False, "tools": True, "structured_output": True, "streaming": True, "cancellation": True}, "limits": {"max_input_bytes": 1048576, "max_output_tokens": 2048, "max_tools": 8, "max_image_bytes": 0}, "unsupported_behavior": "explicit_error"})
    invalid = {"version": "1.0", "provider": "fake", "capabilities": {"text_input": True}, "limits": {}, "unsupported_behavior": "silent_downgrade"}
    with pytest.raises(Exception):
        validator.validate(invalid)


def test_crop_health_contract_distinguishes_candidate_and_authoritative_results() -> None:
    schema = _schema("crop-health-result.schema.json")
    validator = Draft202012Validator(schema)
    evidence = {"release_id": "crop-health-v1", "release_version": "1.0.0", "artifact_sha256": "a" * 64, "labels_sha256": "b" * 64, "preprocessing_sha256": "c" * 64, "quality_gate": "passed", "confidence_gate": "passed", "margin_gate": "passed", "ood_gate": "passed", "field_gate": "passed", "agronomist_gate": "passed"}
    base = {"status": "completed", "result_role": "candidate", "model_id": "crop-health", "model_version": "1.0.0", "inference_location": "browser_wasm", "captured_at": "2026-09-17T10:00:00Z", "field_id": "field-1", "crop": "tomato", "crop_stage": "flowering", "evidence_quality": {"status": "acceptable", "reasons": []}, "candidates": [{"label_id": "healthy", "display_name": "Healthy", "rank": 1, "score": 0.91}], "limitations": ["screening only"], "review_required": True, "content_pack_version": "1", "artifact_sha256": "a" * 64, "release_evidence": evidence}
    validator.validate(base)
    authoritative = dict(base)
    authoritative["result_role"] = "authoritative"
    authoritative["inference_location"] = "server"
    authoritative["review_required"] = False
    validator.validate(authoritative)
    invalid = dict(base)
    invalid.pop("release_evidence")
    with pytest.raises(Exception):
        validator.validate(invalid)
