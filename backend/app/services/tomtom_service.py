import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.tomtom import TomTomLocationPoint
from app.services.geocoding import geocode_location

# Ensure .env is loaded
for _env_candidate in (
    Path(__file__).resolve().parents[2] / ".env",
    Path(__file__).resolve().parents[3] / ".env",
):
    if _env_candidate.is_file():
        load_dotenv(_env_candidate)
        break

logger = logging.getLogger("Metrivon.tomtom_service")


def get_tomtom_api_key() -> str:
    """Retrieves and validates the TomTom API key from backend environment."""
    key = os.getenv("TOMTOM_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="TOMTOM_API_KEY is not configured on the server. Please set it in backend/.env"
        )
    return key


def resolve_location_point(
    location_str: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Optional[Session] = None,
    point_label: str = "Location"
) -> TomTomLocationPoint:
    """
    Resolves either explicit GPS coordinates or a descriptive address/landmark
    string into a validated TomTomLocationPoint.
    """
    # 1. Coordinate input provided directly
    if latitude is not None and longitude is not None:
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid coordinates for {point_label}: latitude {latitude}, longitude {longitude} out of range."
            )
        name = location_str.strip() if location_str and location_str.strip() else f"{point_label} ({latitude:.4f}, {longitude:.4f})"
        return TomTomLocationPoint(
            name=name,
            display_name=location_str.strip() if location_str else f"GPS: {latitude:.5f}, {longitude:.5f}",
            latitude=round(float(latitude), 5),
            longitude=round(float(longitude), 5)
        )

    # 2. Textual address or landmark provided
    if location_str and location_str.strip():
        clean_text = location_str.strip()
        candidates = geocode_location(clean_text, db=db, limit=3)
        if not candidates:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to resolve GPS coordinates for {point_label}: '{clean_text}'. Please provide valid coordinates or a recognized landmark."
            )
        top = candidates[0]
        return TomTomLocationPoint(
            name=top.get("primary_name") or clean_text,
            display_name=top.get("display_name") or clean_text,
            latitude=round(float(top["latitude"]), 5),
            longitude=round(float(top["longitude"]), 5)
        )

    raise HTTPException(
        status_code=422,
        detail=f"Missing location parameter for {point_label}. Provide either a location name or latitude and longitude."
    )


def _classify_traffic_condition(slowdown_pct: float, road_closure: bool = False) -> Tuple[str, str]:
    """Returns (congestion_level, condition_description)"""
    if road_closure:
        return "SEVERE", "Road Closed / Blocked"
    if slowdown_pct >= 55.0:
        return "SEVERE", "Heavy Gridlock / Severe Delay"
    if slowdown_pct >= 35.0:
        return "HIGH", "Heavy Congestion / Slow Flow"
    if slowdown_pct >= 15.0:
        return "MEDIUM", "Moderate Traffic / Minor Slowdown"
    return "LOW", "Smooth Flow / Free Speed"


def _sample_waypoints(points: List[Dict[str, Any]], max_samples: int = 40) -> List[List[float]]:
    """Downsamples high-density polyline points for clean map telemetry payloads."""
    if not points:
        return []
    total = len(points)
    if total <= max_samples:
        return [[round(p["latitude"], 5), round(p["longitude"], 5)] for p in points]
    
    step = total / float(max_samples)
    sampled = []
    for i in range(max_samples):
        idx = min(total - 1, int(round(i * step)))
        p = points[idx]
        sampled.append([round(p["latitude"], 5), round(p["longitude"], 5)])
    
    # Ensure end point is included
    last_pt = points[-1]
    last_coord = [round(last_pt["latitude"], 5), round(last_pt["longitude"], 5)]
    if sampled[-1] != last_coord:
        sampled.append(last_coord)
    return sampled


def get_tomtom_historical_traffic(
    start_location: Optional[str] = None,
    end_location: Optional[str] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    end_latitude: Optional[float] = None,
    end_longitude: Optional[float] = None,
    depart_at: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Fetches historical traffic flow data and Speed Profiles from TomTom Routing API
    for a given corridor between two user-specified locations at a past timestamp.
    """
    api_key = get_tomtom_api_key()

    start_pt = resolve_location_point(
        location_str=start_location,
        latitude=start_latitude,
        longitude=start_longitude,
        db=db,
        point_label="Start Location"
    )
    end_pt = resolve_location_point(
        location_str=end_location,
        latitude=end_latitude,
        longitude=end_longitude,
        db=db,
        point_label="End Location"
    )

    # Resolve departure timestamp (defaults to 7 days ago if omitted)
    if depart_at and depart_at.strip():
        clean_depart = depart_at.strip().replace('"', '').replace("'", "")
    else:
        # 7 days ago at current hour:minute
        clean_depart = (datetime.now() - timedelta(days=7)).replace(microsecond=0).isoformat()

    encoded_depart = urllib.parse.quote(clean_depart)
    url = (
        f"https://api.tomtom.com/routing/1/calculateRoute/"
        f"{start_pt.latitude:.5f},{start_pt.longitude:.5f}:{end_pt.latitude:.5f},{end_pt.longitude:.5f}/json"
        f"?departAt={encoded_depart}&computeTravelTimeFor=all&traffic=true&key={api_key}"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RoadSenseAI/1.0"})
        with urllib.request.urlopen(req, timeout=6.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.error(f"TomTom Historical API request failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"TomTom Traffic API error: {str(exc)}"
        )

    routes = data.get("routes", [])
    if not routes:
        raise HTTPException(
            status_code=404,
            detail="TomTom could not find a drivable route between the provided locations."
        )

    route = routes[0]
    summary = route.get("summary", {})
    length_m = int(summary.get("lengthInMeters", 0))
    travel_time_sec = int(summary.get("travelTimeInSeconds", 0))
    historic_tt_sec = int(summary.get("historicTrafficTravelTimeInSeconds", travel_time_sec))
    no_traffic_sec = int(summary.get("noTrafficTravelTimeInSeconds", travel_time_sec))
    delay_sec = int(summary.get("trafficDelayInSeconds", 0))

    dist_km = round(length_m / 1000.0, 2)
    avg_speed = round(dist_km / (travel_time_sec / 3600.0), 1) if travel_time_sec > 0 else 0.0
    free_flow_speed = round(dist_km / (no_traffic_sec / 3600.0), 1) if no_traffic_sec > 0 else avg_speed

    slowdown_pct = 0.0
    if free_flow_speed > 0:
        slowdown_pct = max(0.0, min(100.0, ((free_flow_speed - avg_speed) / free_flow_speed) * 100.0))

    congestion_lvl, condition_desc = _classify_traffic_condition(slowdown_pct)
    raw_points = route.get("legs", [{}])[0].get("points", [])
    sampled_waypoints = _sample_waypoints(raw_points, max_samples=40)

    return {
        "status": "SUCCESS",
        "source": "TomTom Routing & Historical Speed Profiles API",
        "query_type": "historical",
        "start_point": start_pt.model_dump(),
        "end_point": end_pt.model_dump(),
        "depart_at": summary.get("departureTime", clean_depart),
        "arrival_at": summary.get("arrivalTime"),
        "distance_meters": length_m,
        "distance_km": dist_km,
        "travel_time_seconds": travel_time_sec,
        "travel_time_minutes": round(travel_time_sec / 60.0, 1),
        "historic_traffic_travel_time_seconds": historic_tt_sec,
        "no_traffic_travel_time_seconds": no_traffic_sec,
        "traffic_delay_seconds": delay_sec,
        "traffic_delay_minutes": round(delay_sec / 60.0, 1),
        "average_speed_kmh": avg_speed,
        "free_flow_speed_kmh": free_flow_speed,
        "slowdown_percentage": round(slowdown_pct, 1),
        "congestion_level": congestion_lvl,
        "traffic_condition": condition_desc,
        "route_points_count": len(raw_points),
        "sample_waypoints": sampled_waypoints
    }


def get_tomtom_live_traffic(
    start_location: Optional[str] = None,
    end_location: Optional[str] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    end_latitude: Optional[float] = None,
    end_longitude: Optional[float] = None,
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Fetches real-time live traffic flow telemetry from TomTom Traffic APIs
    by passing location parameters (either start/end route corridor or single location point).
    """
    api_key = get_tomtom_api_key()

    # Determine if this is a route corridor query or single point query
    is_route = (
        (start_location or (start_latitude is not None and start_longitude is not None)) and
        (end_location or (end_latitude is not None and end_longitude is not None))
    )

    if is_route:
        start_pt = resolve_location_point(
            location_str=start_location,
            latitude=start_latitude,
            longitude=start_longitude,
            db=db,
            point_label="Start Location"
        )
        end_pt = resolve_location_point(
            location_str=end_location,
            latitude=end_latitude,
            longitude=end_longitude,
            db=db,
            point_label="End Location"
        )

        # 1. Query TomTom calculateRoute with departAt=now for live corridor travel time & delay
        route_url = (
            f"https://api.tomtom.com/routing/1/calculateRoute/"
            f"{start_pt.latitude:.5f},{start_pt.longitude:.5f}:{end_pt.latitude:.5f},{end_pt.longitude:.5f}/json"
            f"?departAt=now&computeTravelTimeFor=all&traffic=true&key={api_key}"
        )

        try:
            req = urllib.request.Request(route_url, headers={"User-Agent": "RoadSenseAI/1.0"})
            with urllib.request.urlopen(req, timeout=6.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.error(f"TomTom Live Route API error: {exc}")
            raise HTTPException(
                status_code=502,
                detail=f"TomTom Live Traffic API error: {str(exc)}"
            )

        routes = data.get("routes", [])
        if not routes:
            raise HTTPException(
                status_code=404,
                detail="TomTom could not compute a drivable live route between the specified locations."
            )

        route = routes[0]
        summary = route.get("summary", {})
        length_m = int(summary.get("lengthInMeters", 0))
        travel_time_sec = int(summary.get("travelTimeInSeconds", 0))
        no_traffic_sec = int(summary.get("noTrafficTravelTimeInSeconds", travel_time_sec))
        delay_sec = int(summary.get("trafficDelayInSeconds", 0))

        dist_km = round(length_m / 1000.0, 2)
        avg_speed = round(dist_km / (travel_time_sec / 3600.0), 1) if travel_time_sec > 0 else 0.0
        free_flow_speed = round(dist_km / (no_traffic_sec / 3600.0), 1) if no_traffic_sec > 0 else avg_speed

        raw_points = route.get("legs", [{}])[0].get("points", [])
        sampled_waypoints = _sample_waypoints(raw_points, max_samples=40)

        # 2. Query TomTom Flow Segment API at corridor midpoint for sensor-level telemetry
        sensor_confidence = 100.0
        frc = "FRC2"
        road_closure = False
        if raw_points:
            mid_pt = raw_points[len(raw_points) // 2]
            seg_url = (
                f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
                f"?point={mid_pt['latitude']:.5f},{mid_pt['longitude']:.5f}&unit=KMPH&key={api_key}"
            )
            try:
                s_req = urllib.request.Request(seg_url, headers={"User-Agent": "RoadSenseAI/1.0"})
                with urllib.request.urlopen(s_req, timeout=3.5) as s_resp:
                    s_data = json.loads(s_resp.read().decode("utf-8"))
                    flow = s_data.get("flowSegmentData", {})
                    if flow:
                        sensor_confidence = round(float(flow.get("confidence", 1.0)) * 100.0, 1)
                        frc = flow.get("frc", frc)
                        road_closure = bool(flow.get("roadClosure", False))
            except Exception as e:
                logger.debug(f"TomTom Flow Segment midpoint query skipped: {e}")

        slowdown_pct = 0.0
        if free_flow_speed > 0:
            slowdown_pct = max(0.0, min(100.0, ((free_flow_speed - avg_speed) / free_flow_speed) * 100.0))

        congestion_lvl, condition_desc = _classify_traffic_condition(slowdown_pct, road_closure=road_closure)

        return {
            "status": "SUCCESS",
            "source": "TomTom Real-Time Traffic Routing & Sensor Flow API",
            "query_type": "live",
            "start_point": start_pt.model_dump(),
            "end_point": end_pt.model_dump(),
            "monitored_point": None,
            "depart_at": summary.get("departureTime"),
            "arrival_at": summary.get("arrivalTime"),
            "distance_meters": length_m,
            "distance_km": dist_km,
            "current_travel_time_seconds": travel_time_sec,
            "current_travel_time_minutes": round(travel_time_sec / 60.0, 1),
            "free_flow_travel_time_seconds": no_traffic_sec,
            "traffic_delay_seconds": delay_sec,
            "traffic_delay_minutes": round(delay_sec / 60.0, 1),
            "current_speed_kmh": avg_speed,
            "free_flow_speed_kmh": free_flow_speed,
            "slowdown_percentage": round(slowdown_pct, 1),
            "congestion_level": congestion_lvl,
            "traffic_condition": condition_desc,
            "sensor_confidence_score": sensor_confidence,
            "road_closure": road_closure,
            "functional_road_class": frc,
            "route_points_count": len(raw_points),
            "sample_waypoints": sampled_waypoints
        }

    # Case B: Single point live telemetry
    pt = resolve_location_point(
        location_str=location or start_location or end_location,
        latitude=latitude if latitude is not None else start_latitude,
        longitude=longitude if longitude is not None else start_longitude,
        db=db,
        point_label="Location Point"
    )

    seg_url = (
        f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
        f"?point={pt.latitude:.5f},{pt.longitude:.5f}&unit=KMPH&key={api_key}"
    )

    try:
        s_req = urllib.request.Request(seg_url, headers={"User-Agent": "RoadSenseAI/1.0"})
        with urllib.request.urlopen(s_req, timeout=5.0) as s_resp:
            s_data = json.loads(s_resp.read().decode("utf-8"))
    except Exception as exc:
        logger.error(f"TomTom Flow Segment API error: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"TomTom Traffic Flow API error: {str(exc)}"
        )

    flow = s_data.get("flowSegmentData", {})
    if not flow:
        raise HTTPException(
            status_code=404,
            detail=f"No active TomTom sensor segment found for coordinates ({pt.latitude}, {pt.longitude})."
        )

    current_spd = float(flow.get("currentSpeed", 35.0))
    free_flow_spd = float(flow.get("freeFlowSpeed", 40.0))
    curr_tt = int(flow.get("currentTravelTime", 60))
    free_tt = int(flow.get("freeFlowTravelTime", 45))
    delay_sec = max(0, curr_tt - free_tt)
    road_closure = bool(flow.get("roadClosure", False))
    confidence = round(float(flow.get("confidence", 0.95)) * 100.0, 1)

    slowdown_pct = 0.0
    if free_flow_spd > 0:
        slowdown_pct = max(0.0, min(100.0, ((free_flow_spd - current_spd) / free_flow_spd) * 100.0))

    congestion_lvl, condition_desc = _classify_traffic_condition(slowdown_pct, road_closure=road_closure)

    raw_coords = flow.get("coordinates", {}).get("coordinate", [])
    sampled_waypoints = [[c["latitude"], c["longitude"]] for c in raw_coords] if raw_coords else []

    return {
        "status": "SUCCESS",
        "source": "TomTom Real-Time Flow Segment Data API v4",
        "query_type": "live",
        "start_point": None,
        "end_point": None,
        "monitored_point": pt.model_dump(),
        "depart_at": datetime.now().isoformat(),
        "arrival_at": None,
        "distance_meters": None,
        "distance_km": None,
        "current_travel_time_seconds": curr_tt,
        "current_travel_time_minutes": round(curr_tt / 60.0, 1),
        "free_flow_travel_time_seconds": free_tt,
        "traffic_delay_seconds": delay_sec,
        "traffic_delay_minutes": round(delay_sec / 60.0, 1),
        "current_speed_kmh": round(current_spd, 1),
        "free_flow_speed_kmh": round(free_flow_spd, 1),
        "slowdown_percentage": round(slowdown_pct, 1),
        "congestion_level": congestion_lvl,
        "traffic_condition": condition_desc,
        "sensor_confidence_score": confidence,
        "road_closure": road_closure,
        "functional_road_class": flow.get("frc", "FRC2"),
        "route_points_count": len(sampled_waypoints),
        "sample_waypoints": sampled_waypoints[:40]
    }
