"""Explicit, offline-safe downloader for source-verified public model artifacts.

This command does not promote a model to a clinical/agronomic release.  It only
records what was fetched so operators can independently qualify it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .registry import CropDiseaseRegistry, ModelEntry, default_registry_path


def _digest(path: Path) -> str:
    hash_ = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hash_.update(chunk)
    return hash_.hexdigest()


def _write_manifest(entry: ModelEntry, destination: Path) -> None:
    files = [{"path": str(item.relative_to(destination)).replace("\\", "/"), "size_bytes": item.stat().st_size, "sha256": _digest(item)} for item in sorted(destination.rglob("*")) if item.is_file() and item.name != "download-manifest.json"]
    (destination / "download-manifest.json").write_text(json.dumps({"schema_version": "1.0", "model_id": entry.id, "remote_id": entry.remote_id, "revision": entry.revision, "source_url": entry.source_url, "license": entry.license, "downloaded_at": datetime.now(timezone.utc).isoformat(), "files": files}, indent=2) + "\n", encoding="utf-8")


def verify(entry: ModelEntry, destination: Path) -> bool:
    manifest_path = destination / "download-manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest.get("model_id") == entry.id and all((destination / row["path"]).is_file() and _digest(destination / row["path"]) == row["sha256"] for row in manifest["files"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


def download(entry: ModelEntry, root: Path, *, force: bool = False) -> Path:
    if entry.status != "VERIFIED_DOWNLOADABLE" or not entry.remote_id:
        raise ValueError(f"{entry.id} is not a downloadable source artifact")
    destination = root / entry.local_path
    if not force and verify(entry, destination):
        return destination
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError("Install huggingface_hub to run the explicit downloader") from exc
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=entry.remote_id, revision=entry.revision, local_dir=str(destination))
    # Keras inference cannot safely infer class indexes.  Preserve an upstream
    # labels file if supplied; otherwise the adapter stays deliberately blocked.
    if entry.framework == "keras" and not (destination / "labels.json").exists():
        for candidate in (destination / "class_names.json", destination / "labels.txt", destination / "class_names.txt"):
            if candidate.is_file():
                values = json.loads(candidate.read_text(encoding="utf-8")) if candidate.suffix == ".json" else [line.strip() for line in candidate.read_text(encoding="utf-8").splitlines() if line.strip()]
                if isinstance(values, list) and all(isinstance(value, str) for value in values):
                    (destination / "labels.json").write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
                    break
    _write_manifest(entry, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicitly download crop-disease source artifacts")
    parser.add_argument("--registry", type=Path, default=default_registry_path())
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent / "downloaded")
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--crop")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    registry = CropDiseaseRegistry.from_path(args.registry)
    entries = list(registry.entries) if args.all else [registry.get(model) for model in args.model]
    if args.crop:
        entries = [entry for entry in entries if args.crop in entry.crops]
    if not entries:
        parser.error("select --all or one or more --model IDs")
    for entry in entries:
        target = args.root / entry.local_path
        if args.verify:
            print(f"{entry.id}: {'valid' if verify(entry, target) else 'invalid-or-not-installed'}")
        elif entry.status == "VERIFIED_DOWNLOADABLE":
            print(f"{entry.id}: {download(entry, args.root, force=args.force)}")
        else:
            print(f"{entry.id}: skipped ({entry.status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
