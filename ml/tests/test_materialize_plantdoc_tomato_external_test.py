import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from materialize_plantdoc_tomato_external_test import eligible_paths, safe_name


def test_plantdoc_paths_are_limited_to_the_named_test_label_and_image_types():
    paths = [
        "test/Tomato leaf/a.jpg",
        "train/Tomato leaf/b.jpg",
        "test/Tomato leaf/readme.txt",
        "test/Tomato leaf late blight/c.jpeg",
    ]
    assert eligible_paths(paths, "Tomato leaf") == ["test/Tomato leaf/a.jpg"]


def test_plantdoc_output_names_are_windows_safe_and_stable():
    assert safe_name("late_blight", 3, "test/Tomato leaf late blight/name?with=query.jpg") == "late_blight-0003.jpg"
