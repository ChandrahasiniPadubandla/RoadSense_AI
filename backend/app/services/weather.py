import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger("roadsense.weather_service")

# Cache to prevent repetitive external API calls
# Key: (round(lat, 2), round(lng, 2)), Value: (timestamp, weather_dict)
_WEATHER_CACHE: Dict[tuple, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 600  # 10 minutes cache

USER_AGENT = "RoadSenseAI-Backend/1.0 (contact@roadsense.ai)"


def map_wmo_code_to_condition(code: int, rain: float = 0.0) -> str:
    """
    Maps WMO standard weather code to one of the 5 categories trained in the ML model:
    ['Clear', 'Cloudy', 'Light Rain', 'Heavy Rain', 'Fog']
    """
    if code == 0:
        return "Clear"
    elif code in (1, 2, 3):
        return "Cloudy"
    elif code in (45, 48):
        return "Fog"
    elif code in (51, 53, 55, 56, 57, 61, 80):
        return "Light Rain"
    elif code in (63, 65, 66, 67, 81, 82, 95, 96, 99):
        return "Heavy Rain"
    elif rain > 5.0:
        return "Heavy Rain"
    elif rain > 0.0:
        return "Light Rain"
    return "Clear"


def get_live_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetches real-time live meteorological telemetry from Open-Meteo for any GPS coordinate.
    Caches results for 10 minutes. Falls back safely if API is unreachable.
    """
    cache_key = (round(latitude, 2), round(longitude, 2))
    now_ts = time.time()

    if cache_key in _WEATHER_CACHE:
        cached_time, cached_data = _WEATHER_CACHE[cache_key]
        if now_ts - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    fields = "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,visibility,wind_speed_10m"
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude:.4f}&longitude={longitude:.4f}&current={fields}"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        curr = data.get("current", {})
        temp = float(curr.get("temperature_2m", 30.0))
        humidity = float(curr.get("relative_humidity_2m", 50.0))
        rainfall = float(curr.get("precipitation") or curr.get("rain") or 0.0)
        code = int(curr.get("weather_code", 0))
        wind_speed = float(curr.get("wind_speed_10m", 12.0))

        # Convert visibility from meters to kilometers (clamped to ML training bounds: 0.2 - 10.0 km)
        raw_visibility_m = float(curr.get("visibility", 10000.0))
        visibility_km = min(10.0, max(0.2, round(raw_visibility_m / 1000.0, 1)))

        weather_condition = map_wmo_code_to_condition(code, rainfall)

        result = {
            "weather_condition": weather_condition,
            "temperature": round(temp, 1),
            "rainfall": round(rainfall, 2),
            "humidity": round(humidity, 1),
            "visibility": visibility_km,
            "wind_speed": round(wind_speed, 1),
            "is_live": True,
            "source": "Open-Meteo Live API",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        _WEATHER_CACHE[cache_key] = (now_ts, result)
        return result

    except HTTPException:
        raise
    except Exception as err:
        logger.warning("Live weather query failed for (%s, %s): %s. Using baseline meteorological fallback.", latitude, longitude, err)
        fallback = {
            "weather_condition": "Clear",
            "temperature": 29.0,
            "rainfall": 0.0,
            "humidity": 50.0,
            "visibility": 9.0,
            "wind_speed": 11.0,
            "is_live": False,
            "source": "Hyderabad Meteorological Baseline (Fallback)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        _WEATHER_CACHE[cache_key] = (now_ts, fallback)
        return fallback


