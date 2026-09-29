from __future__ import annotations

from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.field_geometry import validate_field_boundary


def _polygon(ring):
    return {"type": "Polygon", "coordinates": [ring]}


def test_accepts_valid_closed_polygon_and_multipolygon():
    ring = [[73.8, 18.5], [73.81, 18.5], [73.81, 18.51], [73.8, 18.5]]
    polygon = _polygon(ring)
    assert validate_field_boundary(polygon) is polygon
    multi = {"type": "MultiPolygon", "coordinates": [[ring], [
        [[74.8, 19.5], [74.81, 19.5], [74.81, 19.51], [74.8, 19.5]]
    ]]}
    assert validate_field_boundary(multi) is multi


@pytest.mark.parametrize("ring", [
    [[73.8, 18.5], [73.81, 18.5], [73.81, 18.51]],  # unclosed
    [[73.8, 18.5], [73.81, 18.5], [73.8, 18.5], [73.8, 18.5]],  # repeated
    [[73.8, 18.5], [73.81, 18.51], [73.8, 18.51], [73.81, 18.5], [73.8, 18.5]],  # crossed
    [[181, 18.5], [181, 18.51], [180, 18.51], [181, 18.5]],  # invalid longitude
    [[73.8, 18.5], [73.81, 18.5], [73.82, 18.5], [73.8, 18.5]],  # zero area
])
def test_rejects_invalid_polygon_rings(ring):
    with pytest.raises(ValueError):
        validate_field_boundary(_polygon(ring))


def test_field_api_rejects_unclosed_geometry_before_persisting():
    with TemporaryDirectory() as tmp:
        settings.FARM_STATE_DB_DIR = tmp
        settings.FARM_STATE_UPLOAD_DIR = tmp
        with TestClient(app) as client:
            headers = {"X-Farmer-ID": "geometry_farmer"}
            invalid = _polygon([[73.8, 18.5], [73.81, 18.5], [73.81, 18.51]])
            response = client.post("/v1/fields", headers=headers, json={
                "name": "East", "area_acres": 2, "boundary_geojson": invalid,
            })
            assert response.status_code == 422
            assert client.get("/v1/fields", headers=headers).json() == []
