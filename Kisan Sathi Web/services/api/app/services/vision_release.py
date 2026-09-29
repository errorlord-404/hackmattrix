"""Load and sign the single approved browser/server vision release."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.validate_release_manifest import ReleaseManifestError, load_document, validate_release_manifest


class VisionReleaseUnavailable(RuntimeError):
    """Raised when no approved, non-expired, verifiable CV release exists."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def load_approved_descriptor(
    manifest_path: Path,
    approvals_path: Path,
    signing_secret: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return a signed public descriptor or fail closed.

    The descriptor contains no filesystem paths or secrets. It is derived from
    the approved manifest and authority record on every request so a stale
    browser cache cannot authorize a release by itself.
    """

    if not signing_secret:
        raise VisionReleaseUnavailable("vision descriptor signing is not configured")
    try:
        validate_release_manifest(
            manifest_path,
            approvals_path,
            require_approved=True,
            verify_artifacts=True,
            now=now,
        )
        manifest_path = Path(manifest_path).resolve()
        manifest = load_document(manifest_path, "release manifest")
    except (ReleaseManifestError, OSError, ValueError) as exc:
        raise VisionReleaseUnavailable(str(exc)) from exc

    release_id = manifest["release_id"]
    preprocessing = manifest["preprocessing"]
    preprocessing_version = preprocessing.get("version") or preprocessing.get("preprocessing_version")
    if not isinstance(preprocessing_version, str) or not preprocessing_version:
        raise VisionReleaseUnavailable("approved release has no preprocessing version")
    artifacts = manifest["artifacts"]
    public_artifacts: dict[str, dict[str, Any]] = {}
    for role in ("model", "labels", "preprocess", "golden"):
        artifact = artifacts.get(role)
        if not isinstance(artifact, dict):
            raise VisionReleaseUnavailable(f"approved release has no {role} artifact")
        path = str(artifact["path"])
        public_artifacts[role] = {
            "url": artifact.get("url") or f"/models/releases/{release_id}/{role}",
            "sha256": artifact["sha256"].lower(),
            "sizeBytes": artifact["size_bytes"],
        }

    descriptor: dict[str, Any] = {
        "status": "approved",
        "activationAllowed": True,
        "releaseId": release_id,
        "manifestSha256": _sha256(manifest_path),
        "expiresAt": manifest["expires_at"],
        "preprocessingVersion": preprocessing_version,
        "preprocessing": preprocessing,
        "thresholds": manifest["thresholds"],
        "cropIds": manifest["crop_ids"],
        "limitations": manifest.get("limitations", []),
        "artifacts": public_artifacts,
        "runtime": manifest["runtime"],
        "signatureAlgorithm": "hmac-sha256",
    }
    descriptor["signature"] = hmac.new(
        signing_secret.encode("utf-8"), _canonical(descriptor), hashlib.sha256
    ).hexdigest()
    return descriptor
