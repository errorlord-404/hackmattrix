"""Fail-closed packaging and staging for model release candidates.

This module deliberately has no ML-framework dependency.  It packages bytes
that have already been trained, exported, quantized, and evaluated; it never
promotes those bytes or writes an approval record.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .contracts import PipelineError, load_json, safe_relative, sha256_file, validate_schema, write_json


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
RELEASE_SCHEMA = PIPELINE_ROOT / "release-bundle.schema.json"
REQUIRED_ARTIFACTS = (
    "onnx",
    "labels",
    "preprocess",
    "evaluation",
    "model_card",
    "license",
    "golden",
)
AUTOMATED_GATES = (
    "artifact_integrity",
    "dataset_contract",
    "static_int8_calibration",
    "evaluation_thresholds",
    "quantization_regression",
    "runtime_parity",
    "rollback_validation",
)
HUMAN_GATES = (
    "agronomist_review",
    "field_representativeness_review",
    "data_rights_and_consent_review",
    "redistribution_review",
    "crop_protection_claim_review",
    "independent_model_validation",
    "accountable_release_owner_approval",
)

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_UNSAFE_IDENTITY = re.compile(r"(?:^|[._-])(placeholder|demo|untrained)(?:$|[._-])", re.IGNORECASE)
_APPROVAL_CLAIMS = {
    "approved",
    "release_approved",
    "release_ready",
    "activation_allowed",
    "diagnostic_use_allowed",
    "production_ready",
}
_RESERVED_FIELDS = {
    "schema_version",
    "status",
    "immutable",
    "created_at",
    "artifacts",
    "approval",
    "integrity",
}
_MEDIA_TYPES = {
    "onnx": "application/onnx",
    "labels": "application/json",
    "preprocess": "application/json",
    "evaluation": "application/json",
    "model_card": "text/markdown",
    "license": "text/plain",
    "golden": "application/json",
}


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise PipelineError("created_at must be an ISO-8601 timestamp with a timezone") from exc
    if parsed.tzinfo is None:
        raise PipelineError("created_at must include a timezone")
    return value


def _reject_unsafe_claims(value: Any, path: str = "candidate") -> None:
    """Reject activation/approval claims and placeholder-like identities."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            field = str(key)
            child_path = f"{path}.{field}"
            if field in _APPROVAL_CLAIMS and child not in (False, None, "false", "pending", "missing"):
                raise PipelineError(f"{child_path} cannot claim approval or activation")
            if field in {"candidate_id", "model_id", "release_id", "kind", "training_status"}:
                if isinstance(child, str) and _UNSAFE_IDENTITY.search(child):
                    raise PipelineError(f"{child_path} cannot identify placeholder, demo, or untrained content")
            if field == "status" and isinstance(child, str) and child.lower() == "approved":
                raise PipelineError(f"{child_path} cannot claim approved status")
            _reject_unsafe_claims(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_unsafe_claims(child, f"{path}[{index}]")


def _artifact_source(root: Path, relative: str, role: str) -> Path:
    if not isinstance(relative, str):
        raise PipelineError(f"artifact {role} path must be a relative string")
    if any(_UNSAFE_IDENTITY.search(part) for part in Path(relative).parts):
        raise PipelineError(f"artifact {role} path cannot refer to placeholder, demo, or untrained content")
    path = safe_relative(root, relative, f"artifact {role} path")
    if path.is_symlink():
        raise PipelineError(f"artifact {role} must not be a symbolic link")
    if not path.is_file() or path.stat().st_size <= 0:
        raise PipelineError(f"artifact {role} must be an existing non-empty file")
    return path


def _normalise_gates(candidate: Mapping[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    supplied = candidate.get("gates", {})
    if not isinstance(supplied, Mapping):
        raise PipelineError("candidate.gates must be an object")
    supplied_automated = supplied.get("automated", {})
    supplied_human = supplied.get("human", {})
    if not isinstance(supplied_automated, Mapping) or not isinstance(supplied_human, Mapping):
        raise PipelineError("candidate gates must contain automated and human objects")
    unknown_automated = set(supplied_automated) - set(AUTOMATED_GATES)
    unknown_human = set(supplied_human) - set(HUMAN_GATES)
    if unknown_automated or unknown_human:
        raise PipelineError(
            "unknown gates: "
            f"automated={sorted(unknown_automated)}, human={sorted(unknown_human)}"
        )
    automated = {
        name: copy.deepcopy(supplied_automated.get(name, {"status": "missing"}))
        for name in AUTOMATED_GATES
    }
    human = {
        name: copy.deepcopy(supplied_human.get(name, {"status": "pending"}))
        for name in HUMAN_GATES
    }
    # Integrity is established by this packager, not accepted as a caller claim.
    automated["artifact_integrity"] = {"status": "passed", "evidence": "manifest artifact hashes"}
    return {"automated": automated, "human": human}


def _validate_candidate_id(candidate_id: Any) -> str:
    if not isinstance(candidate_id, str) or not _ID_PATTERN.fullmatch(candidate_id):
        raise PipelineError("candidate_id must use lowercase letters, digits, dots, underscores, or hyphens")
    if _UNSAFE_IDENTITY.search(candidate_id):
        raise PipelineError("candidate_id cannot identify placeholder, demo, or untrained content")
    return candidate_id


def package_candidate(
    source_root: Path,
    destination: Path,
    *,
    candidate: Mapping[str, Any],
    artifacts: Mapping[str, str],
    created_at: str | None = None,
) -> Path:
    """Build an immutable-by-contract candidate bundle and return its manifest.

    ``artifacts`` paths are resolved under ``source_root``.  The destination is
    created atomically and must not already exist, so a candidate identity can
    never be silently replaced.
    """

    source_root = Path(source_root).resolve()
    destination = Path(destination).resolve()
    if not source_root.is_dir():
        raise PipelineError("source_root must be an existing directory")
    if destination.exists():
        raise PipelineError("candidate destination already exists; candidate bundles are immutable")
    if not isinstance(candidate, Mapping):
        raise PipelineError("candidate metadata must be an object")
    reserved = _RESERVED_FIELDS & set(candidate)
    if reserved:
        raise PipelineError(f"candidate metadata cannot override reserved fields: {sorted(reserved)}")
    _reject_unsafe_claims(candidate)
    candidate_id = _validate_candidate_id(candidate.get("candidate_id"))

    missing = set(REQUIRED_ARTIFACTS) - set(artifacts)
    extra = set(artifacts) - set(REQUIRED_ARTIFACTS)
    if missing or extra:
        raise PipelineError(f"artifact roles mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    sources = {
        role: _artifact_source(source_root, artifacts[role], role)
        for role in REQUIRED_ARTIFACTS
    }

    manifest: dict[str, Any] = copy.deepcopy(dict(candidate))
    manifest.update(
        {
            "schema_version": "1.0",
            "candidate_id": candidate_id,
            "status": "candidate",
            "immutable": True,
            "created_at": _timestamp(created_at),
            "artifacts": {},
            "gates": _normalise_gates(candidate),
            "approval": {
                "approved": False,
                "activation_allowed": False,
                "authority": "docs/APPROVED_RELEASES.json",
            },
        }
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        for role, source in sources.items():
            suffix = "".join(source.suffixes)
            output_relative = f"artifacts/{role}/{role}{suffix}"
            output = safe_relative(staging, output_relative, f"packaged {role} path")
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
            source_hash = sha256_file(source)
            packaged_hash = sha256_file(output)
            if source_hash != packaged_hash:
                raise PipelineError(f"artifact {role} changed while packaging")
            manifest["artifacts"][role] = {
                "path": output_relative,
                "sha256": packaged_hash,
                "size_bytes": output.stat().st_size,
                "media_type": _MEDIA_TYPES[role],
            }

        payload_hash = _canonical_sha256(manifest)
        manifest["integrity"] = {
            "algorithm": "sha256",
            "manifest_payload_sha256": payload_hash,
        }
        schema = load_json(RELEASE_SCHEMA, "release bundle schema")
        validate_schema(manifest, schema, "candidate release bundle")
        write_json(staging / "manifest.json", manifest)
        staging.replace(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return destination / "manifest.json"


def verify_candidate_bundle(manifest_path: Path) -> dict[str, Any]:
    """Validate schema, path containment, complete hashing, and candidate claims."""

    manifest_path = Path(manifest_path).resolve()
    if manifest_path.name != "manifest.json" or not manifest_path.is_file():
        raise PipelineError("candidate manifest must be an existing manifest.json")
    manifest = load_json(manifest_path, "candidate manifest")
    schema = load_json(RELEASE_SCHEMA, "release bundle schema")
    validate_schema(manifest, schema, "candidate release bundle")
    _reject_unsafe_claims(manifest)
    _validate_candidate_id(manifest.get("candidate_id"))
    if manifest.get("status") != "candidate" or manifest.get("immutable") is not True:
        raise PipelineError("registration accepts only immutable candidate bundles")
    approval = manifest.get("approval", {})
    if approval.get("approved") is not False or approval.get("activation_allowed") is not False:
        raise PipelineError("candidate manifest cannot claim approval or activation")

    payload = copy.deepcopy(manifest)
    integrity = payload.pop("integrity", None)
    if not isinstance(integrity, Mapping) or integrity.get("manifest_payload_sha256") != _canonical_sha256(payload):
        raise PipelineError("candidate manifest payload hash does not match")

    bundle_root = manifest_path.parent
    listed: set[str] = set()
    for role in REQUIRED_ARTIFACTS:
        record = manifest["artifacts"][role]
        artifact = safe_relative(bundle_root, record["path"], f"artifact {role} path")
        if artifact.is_symlink() or not artifact.is_file():
            raise PipelineError(f"artifact {role} is missing or symbolic")
        if artifact.stat().st_size != record["size_bytes"]:
            raise PipelineError(f"artifact {role} size does not match manifest")
        if sha256_file(artifact) != record["sha256"]:
            raise PipelineError(f"artifact {role} hash does not match manifest")
        listed.add(artifact.relative_to(bundle_root).as_posix())
    actual = {
        path.relative_to(bundle_root).as_posix()
        for path in bundle_root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != listed:
        raise PipelineError(
            "candidate bundle contains unhashed or missing artifacts: "
            f"unhashed={sorted(actual - listed)}, missing={sorted(listed - actual)}"
        )
    return manifest


def gate_report(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return incomplete and failed gates without changing any gate state."""

    automated = manifest.get("gates", {}).get("automated", {})
    human = manifest.get("gates", {}).get("human", {})
    missing_automated = sorted(
        name for name in AUTOMATED_GATES if automated.get(name, {}).get("status") == "missing"
    )
    failed_automated = sorted(
        name for name in AUTOMATED_GATES if automated.get(name, {}).get("status") == "failed"
    )
    missing_human = sorted(
        name for name in HUMAN_GATES if human.get(name, {}).get("status") == "pending"
    )
    rejected_human = sorted(
        name for name in HUMAN_GATES if human.get(name, {}).get("status") == "rejected"
    )
    return {
        "missing_automated_gates": missing_automated,
        "failed_automated_gates": failed_automated,
        "missing_human_gates": missing_human,
        "rejected_human_gates": rejected_human,
        "all_gates_complete": not (
            missing_automated or failed_automated or missing_human or rejected_human
        ),
    }


def register_candidate(manifest_path: Path, models_root: Path) -> dict[str, Any]:
    """Stage a verified bundle below ``models/candidates`` without approving it."""

    manifest_path = Path(manifest_path).resolve()
    manifest = verify_candidate_bundle(manifest_path)
    models_root = Path(models_root).resolve()
    candidates_root = models_root if models_root.name == "candidates" else models_root / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    destination = safe_relative(candidates_root, manifest["candidate_id"], "candidate registration path")
    if destination.exists():
        raise PipelineError("registered candidate already exists; registration is immutable")

    staging = Path(tempfile.mkdtemp(prefix=f".{manifest['candidate_id']}.", dir=candidates_root))
    shutil.rmtree(staging)
    try:
        shutil.copytree(manifest_path.parent, staging, copy_function=shutil.copyfile)
        staged_manifest = staging / "manifest.json"
        verify_candidate_bundle(staged_manifest)
        staging.replace(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    gates = gate_report(manifest)
    return {
        "candidate_id": manifest["candidate_id"],
        "registration_status": "staged_candidate",
        "registration_path": str(destination),
        "manifest_path": str(destination / "manifest.json"),
        "approved": False,
        "activation_allowed": False,
        "promotion_performed": False,
        "approval_authority": "docs/APPROVED_RELEASES.json",
        **gates,
    }
