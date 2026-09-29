import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from build_reviewed_field_split import approved_items, field_disjoint_split


def queue_item(index: int, group: str, label: str = "healthy"):
    return {"review_item_id": f"item-{index}", "field_group": group, "image": {"available_locally": True}, "farmer_observed_label": label}


def test_only_explicit_expert_approvals_become_split_candidates():
    queue = {"schema_version": "crop-health-review-queue-v1", "items": [queue_item(1, "field-a"), queue_item(2, "field-b")]}
    review = {"schema_version": "crop-health-expert-review-v1", "items": [{"review_item_id": "item-1", "decision": "approved", "agronomist_label": "late_blight"}, {"review_item_id": "item-2", "decision": "rejected"}]}
    selected = approved_items(queue, review)
    assert [item["review_item_id"] for item in selected] == ["item-1"]
    assert selected[0]["agronomist_label"] == "late_blight"


def test_split_keeps_every_field_group_in_one_partition():
    items = [queue_item(index, f"field-{index}") | {"agronomist_label": "healthy"} for index in range(6)]
    split = field_disjoint_split(items, seed=7)
    placement = {item["field_group"]: partition for partition, partition_items in split.items() for item in partition_items}
    assert len(placement) == 6
    assert set(placement.values()) == {"train", "validation", "field_test"}


def test_split_rejects_insufficient_or_label_leaking_field_groups():
    with pytest.raises(ValueError, match="three distinct field groups"):
        field_disjoint_split([queue_item(1, "field-a") | {"agronomist_label": "healthy"}], seed=1)
    items = [queue_item(1, "field-a", "healthy") | {"agronomist_label": "healthy"}, queue_item(2, "field-b", "healthy") | {"agronomist_label": "healthy"}, queue_item(3, "field-c", "blight") | {"agronomist_label": "blight"}]
    with pytest.raises(ValueError, match="labels absent"):
        field_disjoint_split(items, seed=1)
