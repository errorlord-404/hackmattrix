import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from materialize_plantdoc_tomato_specialist import MAX_GIT_SOURCE_PATH_CHARS, label_paths


def test_specialist_materializer_selects_only_requested_split_label_and_safe_paths():
    paths = [
        "train/Tomato leaf/a.jpg",
        "test/Tomato leaf/b.jpg",
        "train/Tomato leaf late blight/c.jpg",
        "train/Tomato leaf/readme.txt",
        "train/Tomato leaf/" + "a" * MAX_GIT_SOURCE_PATH_CHARS + ".jpg",
    ]
    assert label_paths(paths, "train", "Tomato leaf") == ["train/Tomato leaf/a.jpg"]
