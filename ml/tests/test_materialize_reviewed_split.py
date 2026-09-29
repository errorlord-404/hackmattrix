import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from materialize_reviewed_split import materialize_split


def manifest(image: Path, checksum: str):
    item = {"review_item_id": "review-1", "agronomist_label": "Late Blight", "image": {"local_path": str(image), "sha256": checksum}}
    return {"schema_version": "crop-health-field-split-v1", "partitions": {"train": [item], "validation": [], "field_test": []}}


def test_materialization_copies_integrity_checked_files_to_safe_label_folders(tmp_path):
    source = tmp_path / "leaf.jpg"
    source.write_bytes(b"field-photo")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "dataset"
    assert materialize_split(manifest(source, checksum), output) == {"train": 1}
    assert (output / "train" / "late_blight" / "review-1.jpg").read_bytes() == b"field-photo"


def test_materialization_refuses_changed_source_and_nonempty_destination(tmp_path):
    source = tmp_path / "leaf.jpg"
    source.write_bytes(b"field-photo")
    output = tmp_path / "dataset"
    with pytest.raises(ValueError, match="checksum"):
        materialize_split(manifest(source, "wrong"), output)
    output.mkdir()
    (output / "existing.txt").write_text("do not overwrite", encoding="utf-8")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Destination"):
        materialize_split(manifest(source, checksum), output)
