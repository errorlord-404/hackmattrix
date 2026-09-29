from __future__ import annotations

from math import isfinite
from typing import Any


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def _segments_intersect(a, b, c, d) -> bool:
    first = _orientation(a, b, c)
    second = _orientation(a, b, d)
    third = _orientation(c, d, a)
    fourth = _orientation(c, d, b)
    if first * second < 0 and third * fourth < 0:
        return True
    return (
        (first == 0 and _on_segment(a, b, c))
        or (second == 0 and _on_segment(a, b, d))
        or (third == 0 and _on_segment(c, d, a))
        or (fourth == 0 and _on_segment(c, d, b))
    )


def _validate_ring(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, list) or not 4 <= len(value) <= 501:
        raise ValueError("Each boundary ring must contain 3-500 corners and a closing point")
    points: list[tuple[float, float]] = []
    for position in value:
        if not isinstance(position, list) or len(position) not in (2, 3):
            raise ValueError("Each boundary position must be [longitude, latitude] with optional altitude")
        longitude, latitude = position[:2]
        if any(isinstance(number, bool) or not isinstance(number, (int, float)) or not isfinite(number) for number in (longitude, latitude)):
            raise ValueError("Boundary coordinates must be finite numbers")
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError("Boundary coordinates are outside valid longitude/latitude ranges")
        points.append((float(longitude), float(latitude)))
    if points[0] != points[-1]:
        raise ValueError("Boundary rings must close at their first corner")
    if len(set(points[:-1])) != len(points) - 1:
        raise ValueError("Boundary rings cannot repeat a corner")
    twice_area = sum(
        points[index][0] * points[index + 1][1] - points[index + 1][0] * points[index][1]
        for index in range(len(points) - 1)
    )
    if abs(twice_area) < 1e-12:
        raise ValueError("Boundary rings must enclose a non-zero area")
    segments = len(points) - 1
    for first in range(segments):
        for second in range(first + 2, segments):
            if first == 0 and second == segments - 1:
                continue
            if _segments_intersect(points[first], points[first + 1], points[second], points[second + 1]):
                raise ValueError("Boundary rings cannot cross or overlap themselves")
    return points


def validate_field_boundary(value: dict[str, Any]) -> dict[str, Any]:
    """Validate bounded GeoJSON geometry; this does not verify land ownership or survey accuracy."""
    geometry = value.get("geometry", value)
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("boundary_geojson must be a GeoJSON Polygon or MultiPolygon")
    coordinates = geometry.get("coordinates")
    polygons = [coordinates] if geometry["type"] == "Polygon" else coordinates
    if not isinstance(polygons, list) or not 1 <= len(polygons) <= 20:
        raise ValueError("Boundary must contain 1-20 polygons")
    for polygon in polygons:
        if not isinstance(polygon, list) or not 1 <= len(polygon) <= 10:
            raise ValueError("Each boundary polygon must contain 1-10 rings")
        for ring in polygon:
            _validate_ring(ring)
    return value
