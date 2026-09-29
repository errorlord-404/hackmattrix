"""Validate the standalone dependency and computer-vision approval scopes.

The record is intentionally split into two gates:

* ``development-dependencies`` may approve exact package and browser identities
  for local development and reproducible tests.
* ``release-cv`` must contain a separately approved, distributable model
  release.  The current record keeps only quarantined compatibility hashes, so
  production and ``--require-all`` fail closed.

This module uses only the Python standard library so the gate can run before
any standalone dependency installation.  It never downloads or activates a
model; it verifies the hashes of already-present compatibility artifacts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


class ApprovalError(ValueError):
    """Raised when an approval record is incomplete, stale, or unsafe."""


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
INTEGRITY_RE = re.compile(r"^(sha256|sha512)-[A-Za-z0-9+/=]+$")
IMMUTABLE_IMAGE_RE = re.compile(r"^[a-z0-9./-]+:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$")

PLAYWRIGHT_IMAGE = (
    "mcr.microsoft.com/playwright:v1.63.0@"
    "sha256:eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27"
)

EXPECTED_PACKAGES: dict[str, dict[str, Any]] = {
    "PyJWT": {
        "ecosystem": "pypi",
        "version": "2.14.0",
        "registry_url": "https://pypi.org/project/PyJWT/2.14.0/",
        "source_url": "https://github.com/jpadilla/pyjwt",
        "license": "MIT",
        "artifacts": [
            {
                "filename": "pyjwt-2.14.0-py3-none-any.whl",
                "sha256": "ad0cef71c756a56e74863c2919cf0985f72decbcfcb550ee2f422e7c62b5eedc",
                "size_bytes": 32896,
            },
            {
                "filename": "pyjwt-2.14.0.tar.gz",
                "sha256": "77283c83fb56ecf566a886c757a714bc83668e38156de2cce8263302f42e0b86",
                "size_bytes": 113177,
            },
        ],
    },
    "onnxruntime-web": {
        "ecosystem": "npm",
        "version": "1.30.0",
        "registry_url": "https://www.npmjs.com/package/onnxruntime-web/v/1.30.0",
        "source_url": "https://github.com/microsoft/onnxruntime",
        "license": "MIT",
        "artifacts": [
            {
                "filename": "onnxruntime-web-1.30.0.tgz",
                "integrity": "sha512-q0y+JrrtukXSzsBWEMccVfqX25LRmosXHF+CaRJmg8pZClzcV7svNc4rKY3jL02Vb7QmRMDs1SigqR4CXAfKYQ==",
                "shasum": "b88b09117992e6f486321e931a826fd2f7775377",
            }
        ],
    },
    "@playwright/test": {
        "ecosystem": "npm",
        "version": "1.63.0",
        "registry_url": "https://www.npmjs.com/package/@playwright/test/v/1.63.0",
        "source_url": "https://github.com/microsoft/playwright",
        "license": "Apache-2.0",
        "artifacts": [
            {
                "filename": "test-1.63.0.tgz",
                "integrity": "sha512-oxMK4vllB9RK5NQ2l1pq1IfOf2AvnEuj/vYGDj0H2nMtmtZpKtCwt/l00GEO6xjGfpBNAvjovvYdCm50dRQkpQ==",
                "shasum": "808020c46e8b6b91f9d628cd0ebcbb32bdfd8b6c",
            }
        ],
    },
}


def _fail(message: str) -> None:
    raise ApprovalError(message)


def _reject_json_constant(value: str) -> None:
    _fail(f"JSON contains non-standard constant: {value}")


def load_record(path: Path) -> dict[str, Any]:
    """Load a JSON approval record as a strict object."""

    path = Path(path).resolve()
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, parse_constant=_reject_json_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"unable to read approval record: {exc}")
    if not isinstance(value, dict):
        _fail("approval record must be a JSON object")
    return value


def canonical_digest(record: Mapping[str, Any]) -> str:
    """Return the stable digest used by downstream release evidence.

    ``record_digest`` is excluded if a caller adds it as an informational
    field, which prevents a self-referential digest from changing the value.
    """

    normalized = copy.deepcopy(dict(record))
    normalized.pop("record_digest", None)
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{field} must be a non-empty string")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{field} must be a boolean")
    return value


def _sha256(value: Any, field: str) -> str:
    value = _string(value, field).lower()
    if not SHA256_RE.fullmatch(value):
        _fail(f"{field} must be a 64-character SHA-256 hash")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    value = _string(value, field)
    if not value.endswith("Z"):
        _fail(f"{field} must use a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        _fail(f"{field} is not an ISO-8601 timestamp: {exc}")
    if parsed.tzinfo is None:
        _fail(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _safe_path(root: Path, value: Any, field: str) -> Path:
    value = _string(value, field)
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        _fail(f"{field} escapes standalone root")
    if Path(value).is_absolute() or ".." in Path(value).parts:
        _fail(f"{field} must be a relative path without parent traversal")
    return candidate


def _artifact(root: Path, value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{field} must be an artifact object")
    path = _safe_path(root, value.get("path"), f"{field}.path")
    size = value.get("size_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        _fail(f"{field}.size_bytes must be a positive integer")
    expected_hash = _sha256(value.get("sha256"), f"{field}.sha256")
    if not path.is_file():
        _fail(f"{field} is missing: {value['path']}")
    actual_size = path.stat().st_size
    if actual_size != size:
        _fail(f"{field} size mismatch: expected {size}, found {actual_size}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual_hash = digest.hexdigest()
    if actual_hash != expected_hash:
        _fail(f"{field} SHA-256 mismatch")
    return {"path": value["path"], "size_bytes": size, "sha256": expected_hash}


def _validate_review(record: Mapping[str, Any], now: datetime) -> None:
    review = record.get("review")
    if not isinstance(review, dict):
        _fail("review metadata is required")
    reviewer = _string(review.get("reviewer"), "review.reviewer")
    if reviewer.lower() in {"unknown", "placeholder", "todo"}:
        _fail("review.reviewer must identify the approving authority")
    evidence = review.get("reviewer_evidence")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item.strip() for item in evidence):
        _fail("review.reviewer_evidence is required")
    approved_at = _timestamp(review.get("approved_at"), "review.approved_at")
    expires_at = _timestamp(review.get("expires_at"), "review.expires_at")
    if approved_at > now + timedelta(minutes=5):
        _fail("approval record is dated in the future")
    if expires_at <= approved_at:
        _fail("approval record is stale: review.expires_at must be after review.approved_at")
    if expires_at <= now:
        _fail("approval record is expired or stale")


def _validate_integrity(value: Any, field: str) -> None:
    if not isinstance(value, str) or not INTEGRITY_RE.fullmatch(value):
        _fail(f"{field} is missing or is not an exact integrity hash")


def _validate_package(package: Any, expected: Mapping[str, Any]) -> None:
    if not isinstance(package, dict):
        _fail("development package entry must be an object")
    name = expected["name"] if "name" in expected else None
    # The name is checked by the caller; retaining this local check makes the
    # error useful if this function is reused independently.
    if package.get("name") != name:
        _fail(f"package identity mismatch for {name}")
    for field in ("ecosystem", "version", "registry_url", "source_url"):
        if package.get(field) != expected[field]:
            _fail(f"{name} {field} does not match the verified identity")
    if package.get("version") != expected["version"] or any(char in package["version"] for char in "^~*<>"):
        _fail(f"{name} version must be the exact approved version")
    for review_field in ("license_review", "install_script_review"):
        review = package.get(review_field)
        if not isinstance(review, dict) or review.get("status") != "passed" or review.get("reviewed") is not True:
            _fail(f"{name} {review_field} is not approved")
        _string(review.get("evidence_url"), f"{name}.{review_field}.evidence_url")
    if package["license_review"].get("license") != expected["license"]:
        _fail(f"{name} license identity does not match the verified package")

    artifacts = package.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        _fail(f"{name} must record exact artifact hashes")
    by_filename = {item.get("filename"): item for item in artifacts if isinstance(item, dict)}
    for expected_artifact in expected["artifacts"]:
        actual = by_filename.get(expected_artifact["filename"])
        if actual is None:
            _fail(f"{name} is missing artifact hash for {expected_artifact['filename']}")
        if "sha256" in expected_artifact:
            if _sha256(actual.get("sha256"), f"{name}.{expected_artifact['filename']}.sha256") != expected_artifact["sha256"]:
                _fail(f"{name} artifact hash does not match the verified registry hash")
            if actual.get("size_bytes") != expected_artifact["size_bytes"]:
                _fail(f"{name} artifact size does not match the verified registry metadata")
        else:
            _validate_integrity(actual.get("integrity"), f"{name}.{expected_artifact['filename']}.integrity")
            if actual["integrity"] != expected_artifact["integrity"] or actual.get("shasum") != expected_artifact["shasum"]:
                _fail(f"{name} artifact integrity does not match the verified registry hash")


def _validate_development_scope(record: Mapping[str, Any]) -> dict[str, Any]:
    scopes = record.get("scopes")
    if not isinstance(scopes, dict):
        _fail("scopes object is required")
    development = scopes.get("development-dependencies")
    if not isinstance(development, dict):
        _fail("development-dependencies scope is required")
    if development.get("scope") != "development-dependencies":
        _fail("development dependency scope identifier is invalid")
    if development.get("status") != "approved_for_development" or development.get("approved") is not True:
        _fail("development-dependencies scope is not approved")
    if development.get("production_release_approved") is not False:
        _fail("development approval must not imply production release approval")

    packages = development.get("packages")
    if not isinstance(packages, list) or len(packages) != len(EXPECTED_PACKAGES):
        _fail("development scope must contain the complete exact package set")
    by_name = {item.get("name"): item for item in packages if isinstance(item, dict)}
    if set(by_name) != set(EXPECTED_PACKAGES):
        _fail("development scope package identities are incomplete or unexpected")
    for name, expected_base in EXPECTED_PACKAGES.items():
        expected = dict(expected_base)
        expected["name"] = name
        _validate_package(by_name[name], expected)

    image = development.get("browser_image")
    if not isinstance(image, dict):
        _fail("development scope must contain the browser image identity")
    if image.get("repository") != "mcr.microsoft.com/playwright" or image.get("tag") != "v1.63.0":
        _fail("Playwright image repository or tag does not match the verified identity")
    if image.get("version") != "1.63.0":
        _fail("Playwright image version must match @playwright/test 1.63.0")
    digest = _string(image.get("digest"), "browser_image.digest").lower()
    if digest != PLAYWRIGHT_IMAGE.split("@", 1)[1]:
        _fail("Playwright image digest does not match the verified immutable digest")
    reference = _string(image.get("reference"), "browser_image.reference")
    if not IMMUTABLE_IMAGE_RE.fullmatch(reference) or reference != PLAYWRIGHT_IMAGE:
        _fail("Playwright image must use the exact immutable digest reference; mutable tags are rejected")
    if image.get("immutable") is not True or image.get("review_status") != "passed":
        _fail("Playwright image has not passed immutable identity review")
    _string(image.get("registry_url"), "browser_image.registry_url")
    _string(image.get("source_url"), "browser_image.source_url")
    if image.get("registry_url") != "https://mcr.microsoft.com/v2/playwright/manifests/v1.63.0":
        _fail("Playwright image registry URL is not the verified manifest endpoint")
    if image.get("source_url") != "https://github.com/microsoft/playwright":
        _fail("Playwright image source URL is not the verified repository")
    matching = development.get("matching");
    if not isinstance(matching, dict):
        _fail("development scope must record package/image version matching")
    if matching != {
        "onnxruntime-web": "1.30.0",
        "@playwright/test": "1.63.0",
        "playwright_image": PLAYWRIGHT_IMAGE,
    }:
        _fail("development package and browser image versions do not match")
    return {
        "status": "approved_for_development",
        "package_versions": {name: by_name[name]["version"] for name in EXPECTED_PACKAGES},
        "playwright_image": PLAYWRIGHT_IMAGE,
    }


def _validate_manifest_semantics(root: Path, asset: Mapping[str, Any], manifest_path: Path) -> None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"quarantined manifest is unreadable: {exc}")
    if not isinstance(manifest, dict):
        _fail("quarantined manifest must be a JSON object")
    if manifest.get("model_id") != asset.get("model_id") or manifest.get("status") != asset.get("kind"):
        _fail("quarantined manifest identity or status does not match the approval record")
    if manifest.get("enabled") is not False:
        _fail("placeholder manifest must remain disabled")
    approval = manifest.get("approval")
    if not isinstance(approval, dict) or approval.get("release_approved") is not False:
        _fail("placeholder manifest must explicitly deny release approval")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        _fail("placeholder manifest must declare compatibility artifacts")
    for key in ("model", "labels", "golden_fixture"):
        nested = artifacts.get(key)
        listed = asset.get(key)
        if not isinstance(nested, dict) or not isinstance(listed, dict):
            _fail(f"placeholder {key} metadata is incomplete")
        if nested.get("sha256") != listed.get("sha256") or nested.get("size_bytes") != listed.get("size_bytes"):
            _fail(f"placeholder {key} metadata differs from its manifest")
    if asset.get("kind") == "structural_stub_untrained":
        if manifest.get("diagnostic_capability") is not False:
            _fail("structural placeholder must deny diagnostic capability")
        if approval.get("activation_prohibited") is not True:
            _fail("structural placeholder must prohibit activation")
        if manifest.get("model_contract", {}).get("behavior") != "constant_zero_logits_non_diagnostic":
            _fail("structural placeholder must declare constant non-diagnostic behavior")


def _validate_release_cv_scope(record: Mapping[str, Any], root: Path) -> None:
    scopes = record.get("scopes")
    if not isinstance(scopes, dict):
        _fail("scopes object is required")
    release_cv = scopes.get("release-cv")
    if not isinstance(release_cv, dict):
        _fail("release-cv scope is required")
    if release_cv.get("scope") != "release-cv":
        _fail("release-CV scope identifier is invalid")
    if release_cv.get("status") != "deferred_unapproved":
        _fail("release-cv placeholder scope cannot be presented as approved")
    for field in ("approved", "release_ready", "activation_allowed", "diagnostic_use_allowed"):
        if release_cv.get(field) is not False:
            _fail(f"release-cv {field} must remain false for placeholders")
    if release_cv.get("approved_artifacts") is not None:
        _fail("release-cv approved_artifacts must remain null until a distributable release is approved")
    reason = _string(release_cv.get("reason"), "release-cv.reason").lower()
    if "placeholder" not in reason and "research" not in reason and "unapproved" not in reason:
        _fail("release-cv deferral reason must identify the unapproved research/placeholder state")
    gates = release_cv.get("required_release_gates")
    if not isinstance(gates, dict) or not gates:
        _fail("release-cv required release gates are missing")
    if any(value not in {"missing", "not_approved", "deferred"} for value in gates.values()):
        _fail("release-cv required release gates must remain unresolved")

    assets = release_cv.get("quarantined_compatibility_assets")
    if not isinstance(assets, list) or not assets:
        _fail("release-cv must record quarantined compatibility hashes")
    model_ids: set[str] = set()
    for index, asset in enumerate(assets):
        field = f"release-cv.quarantined_compatibility_assets[{index}]"
        if not isinstance(asset, dict):
            _fail(f"{field} must be an object")
        model_id = _string(asset.get("model_id"), f"{field}.model_id")
        if model_id in model_ids:
            _fail(f"duplicate quarantined model: {model_id}")
        model_ids.add(model_id)
        if asset.get("approved") is not False or asset.get("activation_allowed") is not False:
            _fail(f"{field} cannot be approved or activated")
        if asset.get("diagnostic_capability") is not False or asset.get("compatibility_only") is not True:
            _fail(f"{field} must remain compatibility-only and non-diagnostic")
        kind = _string(asset.get("kind"), f"{field}.kind")
        if kind not in {"research_placeholder_unapproved", "structural_stub_untrained"}:
            _fail(f"{field} has an executable or unknown placeholder kind")
        artifacts = asset.get("artifacts")
        if not isinstance(artifacts, dict):
            _fail(f"{field}.artifacts must contain manifest, model, labels, and golden_fixture")
        manifest = _artifact(root, artifacts.get("manifest"), f"{field}.artifacts.manifest")
        model = _artifact(root, artifacts.get("model"), f"{field}.artifacts.model")
        labels = _artifact(root, artifacts.get("labels"), f"{field}.artifacts.labels")
        golden = _artifact(root, artifacts.get("golden_fixture"), f"{field}.artifacts.golden_fixture")
        manifest_path = _safe_path(root, manifest["path"], f"{field}.manifest.path")
        _validate_manifest_semantics(
            root,
            {**asset, **artifacts, "manifest": manifest, "model": model, "labels": labels, "golden_fixture": golden},
            manifest_path,
        )
        if asset.get("crop_id") is not None:
            crop_ids = json.loads(manifest_path.read_text(encoding="utf-8")).get("routing", {}).get("catalog_crop_ids", [])
            if asset["crop_id"] not in crop_ids:
                _fail(f"{field}.crop_id is not present in the placeholder manifest")


def validate_record(
    path: Path,
    *,
    scope: str = "development-dependencies",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one requested scope and return machine-readable gate evidence."""

    record_path = Path(path).resolve()
    record = load_record(record_path)
    if record.get("schema_version") != "1.0":
        _fail("unsupported approval record schema version")
    _string(record.get("record_id"), "record_id")
    policy = record.get("policy")
    if not isinstance(policy, dict):
        _fail("policy object is required")
    for field in ("placeholders_may_be_approved", "placeholders_may_be_activated", "placeholders_may_support_release_readiness"):
        if policy.get(field) is not False:
            _fail(f"policy.{field} must be false")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    _validate_review(record, current)
    root = record_path.parent.parent
    _validate_release_cv_scope(record, root)

    if scope not in {"development-dependencies", "release-cv", "all", "production"}:
        _fail(f"unknown validation scope: {scope}")
    if scope in {"release-cv", "all", "production"}:
        _fail("release-cv scope is deferred and unapproved; production release is blocked")
    development = _validate_development_scope(record)
    return {
        "record_id": record["record_id"],
        "scope": "development-dependencies",
        "status": development["status"],
        "release_cv_approved": False,
        "package_versions": development["package_versions"],
        "playwright_image": development["playwright_image"],
        "approval_record_digest": canonical_digest(record),
    }


def validate_approved_releases(path: Path, **kwargs: Any) -> dict[str, Any]:
    """Compatibility name for downstream plans importing the validator."""

    return validate_record(path, **kwargs)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument(
        "--scope",
        choices=("development-dependencies", "release-cv", "all", "production"),
        default="development-dependencies",
    )
    parser.add_argument("--require", action="append", choices=("pyjwt", "onnxruntime-web", "playwright", "playwright-image"))
    parser.add_argument("--require-all", action="store_true")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--verify-final-locks-and-artifacts", action="store_true")
    parser.add_argument("--print-digest", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    scope = args.scope
    if args.require_all or args.production or args.verify_final_locks_and_artifacts:
        scope = "production" if args.production else "all"
    try:
        report = validate_record(args.record, scope=scope)
        if args.require:
            expected = report["package_versions"]
            for required in args.require:
                if required == "pyjwt" and "PyJWT" not in expected:
                    _fail("PyJWT is not approved")
                if required == "onnxruntime-web" and "onnxruntime-web" not in expected:
                    _fail("onnxruntime-web is not approved")
                if required == "playwright" and "@playwright/test" not in expected:
                    _fail("@playwright/test is not approved")
                if required == "playwright-image" and not report.get("playwright_image"):
                    _fail("Playwright image is not approved")
        # The digest is always included so downstream gates can consume the
        # same machine-readable report whether or not the flag is supplied.
        print(json.dumps(report, sort_keys=True))
        return 0
    except ApprovalError as exc:
        print(f"approved releases: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
