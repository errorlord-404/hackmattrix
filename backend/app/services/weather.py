from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.farm_state.store import iso_now


def _utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)


class WeatherProviderError(RuntimeError):
    pass


def _request_open_meteo(latitude: float, longitude: float) -> dict:
    query = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
        "timezone": "UTC",
        "forecast_days": 5,
    })
    request = Request(f"https://api.open-meteo.com/v1/forecast?{query}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=settings.WEATHER_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # urllib has several platform-specific network exceptions.
        raise WeatherProviderError(f"Open-Meteo request failed: {exc}") from exc


def _normalize(raw: dict, latitude: float, longitude: float, provider: str, warning: str | None = None) -> dict:
    fetched = datetime.now(timezone.utc)
    current_raw = raw.get("current", {})
    hourly_raw = raw.get("hourly", {})
    daily_raw = raw.get("daily", {})
    hourly = []
    times = hourly_raw.get("time", [])
    for index, timestamp in enumerate(times):
        hourly.append({
            "observed_at": timestamp,
            "temperature_c": (hourly_raw.get("temperature_2m") or [None] * len(times))[index],
            "precipitation_probability": (hourly_raw.get("precipitation_probability") or [None] * len(times))[index],
            "precipitation_mm": (hourly_raw.get("precipitation") or [None] * len(times))[index],
            "weather_code": (hourly_raw.get("weather_code") or [None] * len(times))[index],
        })
    daily = []
    daily_times = daily_raw.get("time", [])
    for index, timestamp in enumerate(daily_times):
        daily.append({
            "observed_at": timestamp,
            "temperature_max_c": (daily_raw.get("temperature_2m_max") or [None] * len(daily_times))[index],
            "temperature_min_c": (daily_raw.get("temperature_2m_min") or [None] * len(daily_times))[index],
            "precipitation_mm": (daily_raw.get("precipitation_sum") or [None] * len(daily_times))[index],
            "precipitation_probability": (daily_raw.get("precipitation_probability_max") or [None] * len(daily_times))[index],
            "weather_code": (daily_raw.get("weather_code") or [None] * len(daily_times))[index],
        })
    result = {
        "provider": provider,
        "latitude": latitude,
        "longitude": longitude,
        "observed_at": _utc(current_raw.get("time")).isoformat().replace("+00:00", "Z"),
        "fetched_at": fetched.isoformat().replace("+00:00", "Z"),
        "freshness_seconds": 0,
        "current": {
            "temperature_c": current_raw.get("temperature_2m"),
            "relative_humidity_percent": current_raw.get("relative_humidity_2m"),
            "precipitation_mm": current_raw.get("precipitation"),
            "weather_code": current_raw.get("weather_code"),
            "wind_speed_kmh": current_raw.get("wind_speed_10m"),
        },
        "hourly": hourly,
        "daily": daily,
        "warnings": [warning] if warning else [],
    }
    return result


async def fetch_weather(latitude: float, longitude: float) -> dict:
    provider = settings.WEATHER_PROVIDER.strip().lower()
    if provider == "open_meteo":
        raw = await asyncio.to_thread(_request_open_meteo, latitude, longitude)
        return _normalize(raw, latitude, longitude, "open-meteo")
    if provider == "fixture":
        # Fixture mode is deliberately labelled so consumers never treat it as live data.
        raw = {
            "current": {"time": datetime.now(timezone.utc).isoformat(), "temperature_2m": None,
                        "relative_humidity_2m": None, "precipitation": None, "weather_code": None,
                        "wind_speed_10m": None},
            "hourly": {"time": [], "temperature_2m": [], "precipitation_probability": [], "precipitation": [], "weather_code": []},
            "daily": {"time": [], "temperature_2m_max": [], "temperature_2m_min": [], "precipitation_sum": [],
                      "precipitation_probability_max": [], "weather_code": []},
        }
        return _normalize(raw, latitude, longitude, "fixture:offline-demo", "Offline fixture; values are intentionally unavailable")
    raise WeatherProviderError(f"Weather provider '{settings.WEATHER_PROVIDER}' is not configured")

