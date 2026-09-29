import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from build_diagnosis_review_queue import review_items


def row(**overrides):
    base = {
        "feedback_id": "feedback-1", "request_id": "diagnosis-1", "confirmed_crop": "tomato",
        "label": "late_blight", "correctness": "corrected", "share_for_model_improvement": 1,
        "created_at": "2026-09-08T00:00:00Z", "image_path": "C:/private/leaf.jpg",
        "mime_type": "image/jpeg", "size_bytes": 1234, "checksum": "abc", "field_id": "field-1",
        "image_created_at": "2026-09-07T00:00:00Z",
    }
    return {**base, **overrides}


def test_review_queue_includes_only_consented_label_bearing_feedback_without_path_by_default():
    items = review_items([row(), row(feedback_id="no-consent", share_for_model_improvement=0), row(feedback_id="unknown", correctness="unknown", label=None)], source_store="store-hash")
    assert len(items) == 1
    assert items[0]["source_store"] == "store-hash"
    assert items[0]["field_group"] != "field-1"
    assert items[0]["capture_recorded_at"] == "2026-09-07T00:00:00Z"
    assert items[0]["training_eligibility"] == "requires_agronomist_label_review_and_dataset_split"
    assert "local_path" not in items[0]["image"]


def test_review_queue_includes_local_path_only_when_explicitly_requested(tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"photo")
    item = review_items([row(image_path=str(image))], source_store="store-hash", include_local_paths=True)[0]
    assert item["image"]["available_locally"] is True
    assert item["image"]["local_path"] == str(image)
