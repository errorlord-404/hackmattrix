from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings

class WeatherProviderError(RuntimeError): pass

def _normalize(raw: dict, latitude: float, longitude: float, provider: str, warning: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    current = raw.get("current", {}); hourly_raw = raw.get("hourly", {}); daily_raw = raw.get("daily", {})
    def rows(raw_values: dict, fields: dict[str, str]) -> list[dict]:
        times = raw_values.get("time", []); result = []
        for index, stamp in enumerate(times):
            result.append({"observed_at": stamp, **{name: (raw_values.get(source) or [None] * len(times))[index] for name, source in fields.items()}})
        return result
    return {"provider": provider, "latitude": latitude, "longitude": longitude, "observed_at": current.get("time") or now.isoformat().replace("+00:00", "Z"), "fetched_at": now.isoformat().replace("+00:00", "Z"), "freshness_seconds": 0, "current": {"temperature_c": current.get("temperature_2m"), "relative_humidity_percent": current.get("relative_humidity_2m"), "precipitation_mm": current.get("precipitation"), "weather_code": current.get("weather_code"), "wind_speed_kmh": current.get("wind_speed_10m")}, "hourly": rows(hourly_raw, {"temperature_c": "temperature_2m", "precipitation_probability": "precipitation_probability", "precipitation_mm": "precipitation", "weather_code": "weather_code"}), "daily": rows(daily_raw, {"temperature_max_c": "temperature_2m_max", "temperature_min_c": "temperature_2m_min", "precipitation_mm": "precipitation_sum", "precipitation_probability": "precipitation_probability_max", "weather_code": "weather_code"}), "warnings": [warning] if warning else []}

def _open_meteo(latitude: float, longitude: float) -> dict:
    query = urlencode({"latitude": latitude, "longitude": longitude, "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m", "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code", "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code", "timezone": "UTC", "forecast_days": 5})
    try:
        with urlopen(Request(f"https://api.open-meteo.com/v1/forecast?{query}", headers={"Accept": "application/json"}), timeout=settings.weather_timeout_seconds) as response: return json.loads(response.read().decode("utf-8"))
    except Exception as exc: raise WeatherProviderError("Weather provider request failed.") from exc

async def fetch_weather(latitude: float, longitude: float) -> dict:
    provider = settings.weather_provider.strip().lower()
    if provider == "fixture": return _normalize({"current": {}, "hourly": {}, "daily": {}}, latitude, longitude, "fixture:offline-demo", "Offline fixture; values are intentionally unavailable")
    if provider != "open_meteo": raise WeatherProviderError(f"Weather provider '{settings.weather_provider}' is not configured")
    return _normalize(await asyncio.to_thread(_open_meteo, latitude, longitude), latitude, longitude, "open-meteo")
