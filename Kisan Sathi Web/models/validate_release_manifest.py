"""Validate an approved browser/server CV release descriptor.

This is a release-consumer gate, not a model packager. It never downloads,
copies, edits, or approves model bytes. With no approved CV scope in
``docs/APPROVED_RELEASES.json`` the command fails closed by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReleaseManifestError(ValueError):
    """Raised when an approved release descriptor is incomplete or invalid."""


def _load_document(path: Path, label: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReleaseManifestError(f"unable to read {label}: {exc}") from exc
    try:
        if path.suffix.casefold() in {".yaml", ".yml"}:
            import yaml  # type: ignore

            value = yaml.safe_load(text)
        else:
            value = json.loads(text)
    except (ImportError, OSError, ValueError) as exc:
        raise ReleaseManifestError(f"unable to parse {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseManifestError(f"{label} must be an object")
    return value


load_document = _load_document


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_artifact(root: Path, descriptor: dict[str, Any], role: str, verify: bool) -> dict[str, Any]:
    path_value = descriptor.get("path")
    digest = descriptor.get("sha256")
    size = descriptor.get("size_bytes")
    if not isinstance(path_value, str) or not path_value or Path(path_value).is_absolute() or "\\" in path_value:
        raise ReleaseManifestError(f"{role} path must be a safe relative POSIX path")
    path = (root / path_value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ReleaseManifestError(f"{role} path escapes the release root") from exc
    if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
        raise ReleaseManifestError(f"{role} sha256 must be a 64-character hexadecimal digest")
    if not isinstance(size, int) or size <= 0:
        raise ReleaseManifestError(f"{role} size_bytes must be a positive integer")
    if verify:
        if not path.is_file() or path.is_symlink():
            raise ReleaseManifestError(f"{role} artifact is missing or symbolic: {path_value}")
        if path.stat().st_size != size:
            raise ReleaseManifestError(f"{role} size does not match the descriptor")
        if _sha256(path).casefold() != digest.casefold():
            raise ReleaseManifestError(f"{role} SHA-256 does not match the descriptor")
    return {"path": path_value, "sha256": digest.casefold(), "size_bytes": size}


def _authority_artifacts(authority: dict[str, Any]) -> dict[str, Any]:
    scope = authority.get("scopes", {}).get("release-cv")
    if not isinstance(scope, dict):
        raise ReleaseManifestError("approval record has no release-cv scope")
    if scope.get("approved") is not True or scope.get("release_ready") is not True or scope.get("activation_allowed") is not True:
        raise ReleaseManifestError("release-cv scope is not approved, release-ready, and activation-enabled")
    artifacts = scope.get("approved_artifacts")
    if not isinstance(artifacts, dict):
        raise ReleaseManifestError("approved release artifacts are missing from the authority record")
    return artifacts


def validate_release_manifest(
    manifest_path: Path,
    approvals_path: Path,
    *,
    require_approved: bool = False,
    verify_artifacts: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    authority = _load_document(Path(approvals_path).resolve(), "approval record")
    manifest = _load_document(manifest_path, "release manifest")
    required = {
        "release_id", "status", "expires_at", "artifacts", "preprocessing",
        "crop_ids", "thresholds", "gates", "rollback", "runtime",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ReleaseManifestError(f"release manifest is missing: {missing}")
    if manifest.get("status") != "approved":
        raise ReleaseManifestError("release manifest must have status=approved")
    release_id = manifest.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise ReleaseManifestError("release_id is required")
    if not isinstance(manifest["crop_ids"], list) or not manifest["crop_ids"]:
        raise ReleaseManifestError("crop_ids must be a non-empty list")
    if not isinstance(manifest["preprocessing"], dict) or not isinstance(manifest["runtime"], dict):
        raise ReleaseManifestError("preprocessing and runtime must be objects")
    gates = manifest["gates"]
    if not isinstance(gates, dict) or any(gates.get(name) is not True for name in ("field", "ood", "agronomist", "redistribution", "golden_parity")):
        raise ReleaseManifestError("field, OOD, agronomist, redistribution, and golden_parity gates must all be true")
    rollback = manifest["rollback"]
    if not isinstance(rollback, dict) or rollback.get("validated") is not True or not rollback.get("release_id"):
        raise ReleaseManifestError("a validated rollback release identity is required")
    try:
        expires_at = datetime.fromisoformat(str(manifest["expires_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseManifestError("expires_at must be ISO-8601") from exc
    if expires_at.tzinfo is None:
        raise ReleaseManifestError("expires_at must include a timezone")
    current = now or datetime.now(timezone.utc)
    if expires_at <= current:
        raise ReleaseManifestError("release manifest is expired")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict) or not {"model", "labels", "preprocess", "golden"} <= set(artifacts):
        raise ReleaseManifestError("model, labels, preprocess, and golden artifacts are required")
    checked = {
        role: _safe_artifact(manifest_path.parent, descriptor, role, verify_artifacts)
        for role, descriptor in artifacts.items()
        if isinstance(descriptor, dict)
    }
    if set(checked) != set(artifacts):
        raise ReleaseManifestError("every artifact descriptor must be an object")
    if require_approved:
        approved = _authority_artifacts(authority)
        authority_release = approved.get("release_id")
        if authority_release != release_id:
            raise ReleaseManifestError("approval record release_id does not match the manifest")
        authority_manifest = approved.get("manifest")
        if not isinstance(authority_manifest, dict):
            raise ReleaseManifestError("approval record has no manifest identity")
        if authority_manifest.get("path") != manifest_path.relative_to(Path(approvals_path).resolve().parents[1]).as_posix():
            raise ReleaseManifestError("approval record manifest path does not match the supplied manifest")
        if verify_artifacts and (_sha256(manifest_path).casefold() != str(authority_manifest.get("sha256", "")).casefold()):
            raise ReleaseManifestError("approval record manifest hash does not match the supplied manifest")
    return {
        "status": "approved_release_valid" if require_approved else "release_manifest_valid",
        "release_id": release_id,
        "expires_at": manifest["expires_at"],
        "crop_count": len(manifest["crop_ids"]),
        "artifact_count": len(checked),
        "verified_artifacts": verify_artifacts,
        "approval_checked": require_approved,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--approvals",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "APPROVED_RELEASES.json",
    )
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--verify-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        report = validate_release_manifest(
            args.manifest,
            args.approvals,
            require_approved=args.require_approved,
            verify_artifacts=args.verify_artifacts,
        )
    except ReleaseManifestError as exc:
        print(f"release manifest: FAIL: {exc}")
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
