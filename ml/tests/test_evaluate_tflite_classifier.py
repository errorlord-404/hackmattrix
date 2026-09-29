import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from evaluate_tflite_classifier import accepted_prediction, classification_report, image_files


def test_acceptance_requires_both_probability_and_margin():
    assert accepted_prediction([0.90, 0.05, 0.05], 0.70, 0.15) == (0, 0.90, 0.85)
    assert accepted_prediction([0.52, 0.48], 0.45, 0.15)[0] is None
    assert accepted_prediction([0.65, 0.20, 0.15], 0.70, 0.15)[0] is None


def test_acceptance_rejects_non_probability_output():
    try:
        accepted_prediction([2.0, -1.0], 0.7, 0.15)
    except ValueError as exc:
        assert "probability" in str(exc)
    else:
        raise AssertionError("Expected invalid model scores to be rejected")


def test_report_counts_rejected_supported_cases_and_macro_metrics():
    report = classification_report(["healthy", "blight"], [(0, 0), (0, None), (1, 1), (1, 0)])
    assert report["samples"] == 4
    assert report["accepted_samples"] == 3
    assert report["rejected_supported_samples"] == 1
    assert report["coverage"] == 0.75
    assert report["per_class"]["healthy"]["recall"] == 0.5
    assert report["per_class"]["blight"]["recall"] == 0.5
    assert report["macro_f1"] > 0


def test_image_files_ignores_dataset_manifests(tmp_path):
    (tmp_path / "image.jpg").write_bytes(b"image")
    (tmp_path / "SOURCE_MANIFEST.tsv").write_text("metadata", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "leaf.PNG").write_bytes(b"image")
    assert [path.name for path in image_files(tmp_path)] == ["image.jpg", "leaf.PNG"]
