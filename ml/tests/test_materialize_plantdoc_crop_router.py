import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from materialize_plantdoc_crop_router import crop_paths


def test_crop_router_groups_only_the_requested_split_and_crop_prefix():
    paths = [
        "train/Tomato leaf/a.jpg",
        "test/Tomato leaf/b.jpg",
        "train/TomatoX leaf/c.jpg",
        "train/Tomato leaf/readme.txt",
        "train/Tomato leaf/" + "a" * 200 + ".jpg",
    ]
    assert crop_paths(paths, "train", "Tomato") == ["train/Tomato leaf/a.jpg"]
