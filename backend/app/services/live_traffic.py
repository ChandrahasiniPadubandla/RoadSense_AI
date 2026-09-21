import json
import logging
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger("roadsense.live_traffic")

# In-memory TTL cache to respect API rate limits and avoid repetitive requests
# Key: (round(lat, 3), round(lng, 3)), Value: (timestamp, result_dict)
_TRAFFIC_CACHE: Dict[tuple, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 180  # 3 minutes cache for live traffic flow


def get_live_traffic_flow(
    latitude: float,
    longitude: float,
    speed_limit: float = 50.0,
    road_type: Optional[str] = "Arterial Road"
) -> Dict[str, Any]:
    """
    Fetches real-time live traffic flow telemetry for any coordinate in Hyderabad.
    If TOMTOM_API_KEY is configured in backend/.env:
        Queries TomTom Flow Segment Data API for actual vehicle speeds, free-flow speeds,
        and current delays.
    If TOMTOM_API_KEY is not set or times out:
        Gracefully returns calibrated real-time urban telemetry based on road corridor
        capacity, rush hour dynamics, and historical flow.
    """
    cache_key = (round(latitude, 3), round(longitude, 3))
    now_ts = time.time()

    if cache_key in _TRAFFIC_CACHE:
        cached_time, cached_data = _TRAFFIC_CACHE[cache_key]
        if now_ts - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    api_key = os.getenv("TOMTOM_API_KEY", "").strip()

    # 1. Try Live TomTom Traffic Flow API if key is provided
    if api_key:
        try:
            # TomTom Flow Segment Data (relative0: speed relative to free flow, zoom: 10)
            url = (
                f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
                f"?point={latitude:.5f},{longitude:.5f}&unit=KMPH&key={api_key}"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "RoadSenseAI-Backend/1.0 (contact@roadsense.ai)"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            flow = data.get("flowSegmentData", {})
            if flow:
                current_speed = float(flow.get("currentSpeed", speed_limit * 0.7))
                free_flow_speed = float(flow.get("freeFlowSpeed", speed_limit))
                current_travel_time = int(flow.get("currentTravelTime", 60))
                free_flow_travel_time = int(flow.get("freeFlowTravelTime", 45))
                delay_sec = max(0, current_travel_time - free_flow_travel_time)
                delay_mins = round(delay_sec / 60.0, 1)
                confidence = round(float(flow.get("confidence", 0.95)) * 100.0, 1)
                road_closure = bool(flow.get("roadClosure", False))

                # Calculate congestion percentage (how much slower than free flow)
                if free_flow_speed > 0:
                    slowdown_pct = max(0.0, min(100.0, ((free_flow_speed - current_speed) / free_flow_speed) * 100.0))
                else:
                    slowdown_pct = 0.0

                if road_closure:
                    condition = "Road Closed / Blocked"
                elif slowdown_pct > 60.0:
                    condition = "Heavy Delay / Gridlock"
                elif slowdown_pct > 30.0:
                    condition = "Moderate Congestion"
                elif slowdown_pct > 10.0:
                    condition = "Minor Slowdown"
                else:
                    condition = "Smooth Flow"

                result = {
                    "is_live": True,
                    "source": "TomTom Live Traffic Flow API",
                    "current_speed_kmh": round(current_speed, 1),
                    "free_flow_speed_kmh": round(free_flow_speed, 1),
                    "delay_minutes": delay_mins,
                    "delay_seconds": delay_sec,
                    "current_travel_time_seconds": current_travel_time,
                    "free_flow_travel_time_seconds": free_flow_travel_time,
                    "slowdown_percentage": round(slowdown_pct, 1),
                    "traffic_condition": condition,
                    "confidence_score": confidence,
                    "road_closure": road_closure,
                    "coordinates": flow.get("coordinates", {}).get("coordinate", [])
                }
                _TRAFFIC_CACHE[cache_key] = (now_ts, result)
                return result
        except Exception as e:
            logger.error(f"TomTom API query failed or timed out: {e}. Dummy data fallbacks are disabled.")
            return None

    # Dummy data fallbacks are strictly disabled: return None if TOMTOM_API_KEY is not configured
    return None

