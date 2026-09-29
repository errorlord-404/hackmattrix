from types import SimpleNamespace

from app.services.crop_planning import compare_crop_options


def test_crop_option_comparison_reports_missing_evidence_without_inventing_fit():
    crop = SimpleNamespace(
        name="Paddy", season="Kharif", soil_compatibility=[], previous_crop_compatibility=[],
        avg_price_per_quintal=2379.0, source="official", source_url="https://example.test",
    )
    result = compare_crop_options([crop], season="Kharif", previous_crop="Wheat", soil_type=None)[0]
    assert result["checks"]["season"] is True
    assert result["checks"]["previous_crop_rotation"] is None
    assert result["missing_evidence"] == ["previous_crop_rotation", "soil_type"]
    assert result["status"] == "candidate_needs_review"


def test_crop_option_comparison_exposes_known_conflict():
    crop = SimpleNamespace(
        name="Crop", season="Rabi", soil_compatibility=["loam"], previous_crop_compatibility=["any"],
        avg_price_per_quintal=None, source="official", source_url=None,
    )
    result = compare_crop_options([crop], season="Kharif", previous_crop="Wheat", soil_type="loam")[0]
    assert result["conflicts"] == ["season"]
    assert result["status"] == "not_recommended_with_current_inputs"
