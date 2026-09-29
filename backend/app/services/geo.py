from __future__ import annotations

import math
import re


def normalize_admin(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\([^)]*\)", "", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def haversine_km(lat1: float, lon1: float, lat2: float | None, lon2: float | None) -> float | None:
    if lat2 is None or lon2 is None:
        return None
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    value = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1 - value))), 2)
