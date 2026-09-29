from datetime import datetime, timezone

from app.farm_state.rules import irrigation_rule, offline_irrigation_rule


def test_offline_catalog_uses_crop_band_without_weather_input():
    result = offline_irrigation_rule(29, "Tomato", "vegetative", now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result.decision_mode == "offline_catalog"
    assert result.catalog_crop == "tomato"
    assert (result.lower_moisture_percent, result.target_moisture_percent, result.upper_moisture_percent) == (30, 40, 50)
    assert result.status == "recommended"


def test_offline_catalog_never_recommends_watering_at_or_above_upper_bound():
    result = offline_irrigation_rule(51, "Tomato", "vegetative")
    assert result.status == "above_upper_limit"
    assert result.application_adjustment_percent == 0


def test_critical_dry_moisture_is_not_deferred_only_for_rain_probability():
    result = irrigation_rule(19, 95, None, now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result.status == "recommended"
    assert "not enough to defer" in result.why


def test_small_deficit_can_defer_for_location_matched_rain_signal():
    result = irrigation_rule(31, 95, None, now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result.status == "defer_for_rain"


def test_recent_irrigation_requires_reassessment_when_not_critical():
    result = irrigation_rule(31, None, None, recent_irrigation=True, now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result.status == "reassess_after_recent_irrigation"


def test_heavy_rain_with_small_moisture_deficit_defers_to_avoid_waterlogging():
    result = irrigation_rule(
        31, 10, None, now=datetime(2026, 9, 8, tzinfo=timezone.utc),
        rainfall_mm_next_48h=32, rain_probability_next_48h=85,
    )
    assert result.status == "defer_for_heavy_rain"
    assert result.application_adjustment_percent == 0
    assert "32.0 mm" in result.why


def test_critical_dry_soil_uses_only_small_emergency_split_before_heavy_rain():
    result = irrigation_rule(
        18, 30, None, now=datetime(2026, 9, 8, tzinfo=timezone.utc),
        rainfall_mm_next_48h=30, rain_probability_next_48h=80,
    )
    assert result.status == "reduce_for_heavy_rain"
    assert result.application_adjustment_percent == 25


def test_heavy_rain_does_not_create_waterlogging_decision_without_forecast_amount():
    result = irrigation_rule(
        31, 95, None, now=datetime(2026, 9, 8, tzinfo=timezone.utc),
        rain_probability_next_48h=95,
    )
    assert result.status == "defer_for_rain"
