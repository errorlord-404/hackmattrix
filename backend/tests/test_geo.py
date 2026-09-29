from app.services.geo import haversine_km, normalize_admin


def test_normalize_admin_removes_demo_annotation():
    assert normalize_admin(" Maharashtra (local demo) ") == "Maharashtra"
    assert normalize_admin("Pune") == "Pune"


def test_haversine_distance_is_zero_for_same_point_and_bounded_for_nearby_point():
    assert haversine_km(18.5204, 73.8567, 18.5204, 73.8567) == 0.0
    distance = haversine_km(18.5204, 73.8567, 18.53, 73.86)
    assert distance is not None
    assert 0 < distance < 2
