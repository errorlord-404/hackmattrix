import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from compare_tflite_candidates import comparison_rows, validate_comparable_reports


def report(*, macro_f1: float, coverage: float = 0.9, samples: int = 40, score: float = 0.7, unknown_samples: int = 12):
    return {"samples": samples, "accepted_accuracy": 0.9, "coverage": coverage, "macro_f1": macro_f1, "acceptance_policy": {"minimum_score": score, "minimum_margin": 0.15}, "confusion_matrix": {"labels": ["healthy", "late_blight"]}, "unknown_ood": {"samples": unknown_samples, "true_rejection_rate": 0.8}}


def test_comparison_requires_identical_evaluation_scope():
    errors = validate_comparable_reports({"mobile": report(macro_f1=0.8), "efficient": report(macro_f1=0.82, score=0.8)})
    assert errors == ["efficient uses a different score/margin acceptance policy."]


def test_comparison_orders_only_comparable_candidates_by_macro_f1_then_coverage():
    reports = {"mobile": report(macro_f1=0.8, coverage=0.95), "efficient": report(macro_f1=0.82, coverage=0.7)}
    assert validate_comparable_reports(reports) == []
    assert [row["candidate"] for row in comparison_rows(reports)] == ["efficient", "mobile"]
