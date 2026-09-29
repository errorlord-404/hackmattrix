"""Compare only like-for-like TFLite field-evaluation reports.

This utility does not select or approve a crop-health model. It prevents a
controlled-image score, a different threshold, or a different OOD challenge
set from being presented as an accuracy comparison between TF Hub backbones.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_comparable_reports(reports: dict[str, dict[str, Any]]) -> list[str]:
    """Return evidence mismatches that make a cross-candidate ranking invalid."""
    if len(reports) < 2:
        return ["At least two candidate reports are required for comparison."]
    reference_name, reference = next(iter(reports.items()))
    required = ("samples", "macro_f1", "coverage", "acceptance_policy", "confusion_matrix", "unknown_ood")
    errors: list[str] = []
    for name, report in reports.items():
        missing = [key for key in required if key not in report]
        if missing:
            errors.append(f"{name} is missing required report fields: {', '.join(missing)}")
    if errors:
        return errors
    reference_labels = reference["confusion_matrix"].get("labels")
    reference_unknown = reference["unknown_ood"]
    for name, report in reports.items():
        if name == reference_name:
            continue
        if report["samples"] != reference["samples"]:
            errors.append(f"{name} uses {report['samples']} supported samples; {reference_name} uses {reference['samples']}.")
        if report["acceptance_policy"] != reference["acceptance_policy"]:
            errors.append(f"{name} uses a different score/margin acceptance policy.")
        if report["confusion_matrix"].get("labels") != reference_labels:
            errors.append(f"{name} uses a different ordered supported label list.")
        candidate_unknown = report["unknown_ood"]
        if candidate_unknown.get("status") != reference_unknown.get("status") or candidate_unknown.get("samples") != reference_unknown.get("samples"):
            errors.append(f"{name} uses a different unknown/OOD evaluation scope.")
    return errors


def comparison_rows(reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a transparent metric table after comparability validation."""
    rows = []
    for name, report in reports.items():
        unknown = report["unknown_ood"]
        rows.append({"candidate": name, "macro_f1": report["macro_f1"], "coverage": report["coverage"], "accepted_accuracy": report.get("accepted_accuracy"), "unknown_ood_true_rejection_rate": unknown.get("true_rejection_rate"), "model": report.get("model")})
    return sorted(rows, key=lambda row: (-row["macro_f1"], -row["coverage"], row["candidate"]))


def parse_candidate(value: str) -> tuple[str, Path]:
    try:
        name, raw_path = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use NAME=PATH for every --report.") from exc
    if not name.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("Candidate name and report path are required.")
    return name.strip(), Path(raw_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, type=parse_candidate, metavar="NAME=PATH", help="A JSON report written by evaluate_tflite_classifier.py; specify at least twice.")
    parser.add_argument("--output", type=Path, help="Optional JSON comparison output.")
    args = parser.parse_args()
    reports: dict[str, dict[str, Any]] = {}
    for name, path in args.report:
        if name in reports:
            raise SystemExit(f"Duplicate candidate name: {name}")
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Cannot read {name} report at {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise SystemExit(f"{name} report must be a JSON object.")
        reports[name] = loaded
    errors = validate_comparable_reports(reports)
    result = {"comparable": not errors, "errors": errors, "rows": comparison_rows(reports) if not errors else [], "decision_boundary": "This table is evidence only. Require target-device latency/battery, artifact integrity, and agronomist review before any release-manifest decision."}
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
