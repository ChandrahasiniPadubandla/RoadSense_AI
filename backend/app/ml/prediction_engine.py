import os
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from fastapi import HTTPException
from app.database.models import Road, Accident, AccidentHotspot, TrafficRecord
from app.services.geocoding import (
    geocode_location,
    reverse_geocode,
    find_nearest_road_by_coordinates,
    get_driving_route,
    get_accidents_along_route,
    get_or_create_road_from_geocoding,
    is_within_geocoding_boundary
)
from app.services.weather import get_live_weather
from app.services.live_traffic import get_live_traffic_flow


def format_estimated_time(target_time: datetime, duration_minutes: int = 60) -> str:
    """
    Formats the estimated time range as requested:
    e.g. "4:00 PM - 5:00 PM (4pm to 5pm)"
    """
    start_str = target_time.strftime("%I:%M %p").lstrip("0")
    end_time = target_time + timedelta(minutes=duration_minutes)
    end_str = end_time.strftime("%I:%M %p").lstrip("0")
    start_hr = target_time.strftime("%I %p").lstrip("0").lower()
    end_hr = end_time.strftime("%I %p").lstrip("0").lower()
    return f"{start_str} - {end_str} ({start_hr} to {end_hr})"


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates approximate distance between two GPS coordinates in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def compute_temporal_traffic_projection(
    target_time: datetime,
    road_capacity: int = 1500,
    speed_limit: float = 50.0,
    rainfall: float = 0.0,
    accident_count: int = 0,
    live_traffic: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Dynamically projects traffic metrics (speed, density, vehicle count, congestion tier)
    for any target prediction time window.
    - If target_time is current / near-term (<= 60 mins ahead), smoothly blends with
      the latest shared-database traffic observation using a temporal decay window.
    - If target_time is in the future (> 60 mins ahead, e.g. 330 mins / 5.5 hours),
      forecasts based on Hyderabad urban diurnal rush patterns, target hour, day of week,
      road capacity, and weather forecast without being distorted by the present moment.
    """
    now = datetime.now()
    if target_time and target_time.tzinfo is not None:
        target_time = target_time.astimezone().replace(tzinfo=None)
    delta_mins = max(0.0, (target_time - now).total_seconds() / 60.0)

    hour_val = target_time.hour
    day_val = target_time.strftime("%A")
    is_weekend = day_val in ["Saturday", "Sunday"]

    # Hyderabad urban diurnal rush-hour pattern
    if 8 <= hour_val <= 11:
        rush_factor = 0.85 if is_weekend else 1.35   # Morning peak
    elif 17 <= hour_val <= 20:
        rush_factor = 0.95 if is_weekend else 1.50   # Evening rush peak
    elif hour_val == 21:
        rush_factor = 0.85 if is_weekend else 1.15   # Evening post-peak tapering
    elif 12 <= hour_val <= 16:
        rush_factor = 0.80 if is_weekend else 0.95   # Midday flow
    elif hour_val >= 22 or hour_val <= 5:
        rush_factor = 0.28                           # Late night / early morning clear flow
    else:
        rush_factor = 0.65                           # Transition hours

    # Weather & historical incident impact
    weather_factor = 1.30 if rainfall > 5.0 else (1.15 if rainfall > 0.5 else 1.0)
    accident_factor = 1.0 + min(accident_count * 0.05, 0.35)

    # Standardized capacity & volume matching ML model scale
    std_capacity = max(1000, min(int(road_capacity * 0.55), 1800))
    base_vol = std_capacity * 0.50
    effective_vol = base_vol * rush_factor * weather_factor * accident_factor

    temp_vehicles = int(min(max(effective_vol, 120), std_capacity * 1.35))
    temp_density = round(min(max((temp_vehicles / std_capacity) * 100.0, 15.0), 125.0), 2)

    # Empirical speed inversely proportional to congestion
    spd_limit = float(speed_limit or 50.0)
    if temp_density > 85.0:
        calc_speed = max(12.0, spd_limit * 0.35 - (temp_density - 85) * 0.3)
    elif temp_density > 60.0:
        calc_speed = max(20.0, spd_limit * 0.60 - (temp_density - 60) * 0.4)
    elif temp_density > 40.0:
        calc_speed = max(32.0, spd_limit * 0.80 - (temp_density - 40) * 0.3)
    else:
        calc_speed = min(spd_limit, spd_limit * 0.95 + (40 - temp_density) * 0.2)
    temp_speed = round(calc_speed, 2)

    # Horizon weight for live telemetry (decay from 1.0 at 0m to 0.0 at 60m)
    if live_traffic and live_traffic.get("is_live") and any(
        live_traffic.get(field) is not None
        for field in ("current_speed_kmh", "traffic_density", "vehicle_count")
    ):
        w_live = max(0.0, min(1.0, 1.0 - (delta_mins / 60.0)))
        observed_speed = live_traffic.get("current_speed_kmh")
        live_speed = float(observed_speed) if observed_speed is not None else temp_speed
        slowdown_pct = float(live_traffic.get("slowdown_percentage", 0.0))
        observed_density = live_traffic.get("traffic_density")
        live_density = round(
            min(120.0, max(15.0, float(observed_density)))
            if observed_density is not None
            else min(120.0, max(15.0, 28.0 + (slowdown_pct * 0.85))),
            2,
        )
        observed_vehicles = live_traffic.get("vehicle_count")
        live_vehicles = max(
            0,
            int(observed_vehicles)
            if observed_vehicles is not None
            else int(std_capacity * (live_density / 100.0)),
        )

        final_speed = round(w_live * live_speed + (1.0 - w_live) * temp_speed, 1)
        final_density = round(w_live * live_density + (1.0 - w_live) * temp_density, 1)
        final_vehicles = int(w_live * live_vehicles + (1.0 - w_live) * temp_vehicles)
    else:
        final_speed = temp_speed
        final_density = temp_density
        final_vehicles = temp_vehicles

    if final_density > 85.0:
        cong = "SEVERE"
    elif final_density > 65.0:
        cong = "HIGH"
    elif final_density > 45.0:
        cong = "MEDIUM"
    else:
        cong = "LOW"

    return {
        "vehicle_count": final_vehicles,
        "average_speed": final_speed,
        "traffic_density": final_density,
        "predicted_congestion": cong,
        "std_capacity": std_capacity
    }


def resolve_route_bundle(
    db: Session,
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
    end_lat: Optional[float] = None,
    end_lng: Optional[float] = None,
    start_name: Optional[str] = None,
    end_name: Optional[str] = None,
    road_id: Optional[Any] = None,
    target_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Gathers and packages all required data for the ML model:
    - Latitude & Longitude of start and end locations
    - Road conditions & capacity
    - Live weather condition from weather API / records
    - Previous traffic records
    - Historical accident statistics
    - Temporal features (hour, day of week, holiday)
    """
    now = datetime.now()
    if target_time is None:
        target_time = now + timedelta(minutes=30)
    elif target_time.tzinfo is not None:
        target_time = target_time.astimezone().replace(tzinfo=None)

    # 1. If road_id is explicitly provided, query the road entity first
    road = None
    if road_id:
        road = db.query(Road).filter(Road.road_id == road_id).first()
        if not road:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ROAD_NOT_FOUND",
                    "message": f"Road with ID '{road_id}' was not found in the database.",
                    "field": "road_id"
                }
            )
        if start_lat is None and road.start_location is not None:
            pt = to_shape(road.start_location)
            start_lat = pt.y
            start_lng = pt.x
        if end_lat is None and road.end_location is not None:
            pt = to_shape(road.end_location)
            end_lat = pt.y
            end_lng = pt.x
        if not start_name:
            start_name = road.road_name
        if not end_name:
            end_name = road.road_name

    if not road_id and start_name and end_name and start_name.strip().lower() == end_name.strip().lower():
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "IDENTICAL_LOCATIONS",
                "message": f"Start location and destination cannot be identical ('{start_name.strip()}'). Please provide two distinct locations.",
                "field": "end_location"
            }
        )

    # 2. Resolve real latitude & longitude
    s_lat = start_lat
    s_lng = start_lng
    e_lat = end_lat
    e_lng = end_lng

    start_geo_res = None
    end_geo_res = None

    # Dynamic Geocoding & Local Database Route Resolution
    if (s_lat is None or s_lng is None) and start_name:
        clean_s = start_name.strip()
        matched_s = db.query(Road).filter(Road.road_name.ilike(f"%{clean_s}%")).first()
        if not matched_s and "road" in clean_s.lower():
            matched_s = db.query(Road).filter(Road.road_name.ilike(f"%{clean_s.lower().replace('road','').strip()}%")).first()
        if matched_s and matched_s.start_location is not None:
            pt = to_shape(matched_s.start_location)
            s_lat, s_lng = pt.y, pt.x
            if not road:
                road = matched_s
        else:
            start_geo_res = geocode_location(start_name, db=db)
            if not start_geo_res:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "LOCATION_NOT_FOUND",
                        "message": f"Start location '{clean_s}' does not exist in geocoding records. Please provide a valid road or landmark.",
                        "field": "start_location"
                    }
                )
            s_lat = start_geo_res[0]["latitude"]
            s_lng = start_geo_res[0]["longitude"]

    if (e_lat is None or e_lng is None) and end_name:
        clean_e = end_name.strip()
        matched_e = db.query(Road).filter(Road.road_name.ilike(f"%{clean_e}%")).first()
        if not matched_e and "road" in clean_e.lower():
            matched_e = db.query(Road).filter(Road.road_name.ilike(f"%{clean_e.lower().replace('road','').strip()}%")).first()
        if matched_e and matched_e.end_location is not None:
            pt = to_shape(matched_e.end_location)
            e_lat, e_lng = pt.y, pt.x
        elif matched_e and matched_e.start_location is not None:
            pt = to_shape(matched_e.start_location)
            e_lat, e_lng = pt.y, pt.x
        else:
            end_geo_res = geocode_location(end_name, db=db)
            if not end_geo_res:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "LOCATION_NOT_FOUND",
                        "message": f"End location '{clean_e}' does not exist in geocoding records. Please provide a valid road or landmark.",
                        "field": "end_location"
                    }
                )
            e_lat = end_geo_res[0]["latitude"]
            e_lng = end_geo_res[0]["longitude"]

    # If start is resolved but end was not specified, create a realistic corridor offset
    if (s_lat is not None and s_lng is not None) and (e_lat is None or e_lng is None):
        if end_name:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "LOCATION_NOT_FOUND",
                    "message": f"End location '{end_name.strip()}' could not be resolved in geocoding.",
                    "field": "end_location"
                }
            )
        e_lat = round(s_lat + 0.0050, 6)
        e_lng = round(s_lng + 0.0050, 6)

    # If end is resolved but start was not specified, create a realistic corridor offset
    if (e_lat is not None and e_lng is not None) and (s_lat is None or s_lng is None):
        if start_name:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "LOCATION_NOT_FOUND",
                    "message": f"Start location '{start_name.strip()}' could not be resolved in geocoding.",
                    "field": "start_location"
                }
            )
        s_lat = round(e_lat - 0.0050, 6)
        s_lng = round(e_lng - 0.0050, 6)

    # Strict check: Coordinates must be resolvable
    if s_lat is None or s_lng is None or e_lat is None or e_lng is None:
        missing_term = start_name or end_name or "unspecified location"
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "GEOCODING_FAILED",
                "message": f"Coordinates could not be resolved for '{missing_term}'. Please specify a valid road, landmark, or exact latitude/longitude.",
                "field": "start_location" if s_lat is None else "end_location"
            }
        )

    # Check for identical resolved coordinates
    if abs(s_lat - e_lat) < 0.0001 and abs(s_lng - e_lng) < 0.0001:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "IDENTICAL_LOCATIONS",
                "message": "Start location and destination resolve to the exact same point. Please provide two distinct locations.",
                "field": "end_location"
            }
        )

    # Restrict locations strictly to the Hyderabad metropolitan boundary
    if not is_within_geocoding_boundary(s_lat, s_lng):
        start_disp = start_name or f"[{s_lat}, {s_lng}]"
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LOCATION_OUTSIDE_HYDERABAD",
                "message": f"Start location '{start_disp}' is outside Hyderabad. RoadSense AI traffic models are restricted exclusively to the Hyderabad metropolitan region.",
                "field": "start_location"
            }
        )
    if not is_within_geocoding_boundary(e_lat, e_lng):
        end_disp = end_name or f"[{e_lat}, {e_lng}]"
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LOCATION_OUTSIDE_HYDERABAD",
                "message": f"Destination '{end_disp}' is outside Hyderabad. RoadSense AI traffic models are restricted exclusively to the Hyderabad metropolitan region.",
                "field": "end_location"
            }
        )

    # Preserve the user's provided location name if available
    start_label = (start_name or "").strip()
    if not start_label:
        if start_geo_res:
            start_label = start_geo_res[0].get("primary_name") or start_geo_res[0].get("display_name")
        elif s_lat is not None and s_lng is not None:
            rev = reverse_geocode(s_lat, s_lng)
            if rev:
                start_label = rev.get("road") or rev.get("suburb") or rev.get("neighbourhood") or rev.get("display_name")
    if not start_label and s_lat is not None and s_lng is not None:
        start_label = f"Location [{s_lat:.4f}, {s_lng:.4f}]"

    end_label = (end_name or "").strip()
    if not end_label:
        if end_geo_res:
            end_label = end_geo_res[0].get("primary_name") or end_geo_res[0].get("display_name")
        elif e_lat is not None and e_lng is not None:
            rev = reverse_geocode(e_lat, e_lng)
            if rev:
                end_label = rev.get("road") or rev.get("suburb") or rev.get("neighbourhood") or rev.get("display_name")
    if not end_label and e_lat is not None and e_lng is not None:
        end_label = f"Location [{e_lat:.4f}, {e_lng:.4f}]"

    # 3. Match existing Road entity from database or construct dynamic corridor
    newly_created_roads = []
    created_new_road = False

    def find_road_in_db(name: Optional[str]) -> Optional[Road]:
        if not name or len(name.strip()) < 2:
            return None
        clean = name.strip()
        # 1. Exact substring match
        r = db.query(Road).filter(Road.road_name.ilike(f"%{clean}%")).first()
        if r:
            return r
        # 2. Check parts split by comma (e.g. "Uppal Main Road, Hyderabad" -> "Uppal Main Road")
        parts = [p.strip() for p in clean.split(",") if len(p.strip()) >= 3 and p.strip().lower() not in ["hyderabad", "telangana", "india", "medchal-malkajgiri", "medchal", "secunderabad", "rangareddy"]]
        for p in parts:
            r = db.query(Road).filter(Road.road_name.ilike(f"%{p}%")).first()
            if r:
                return r
            if "road" in p.lower():
                short = p.lower().replace("road", "").strip()
                if len(short) >= 3:
                    r = db.query(Road).filter(Road.road_name.ilike(f"%{short}%")).first()
                    if r:
                        return r
        # 3. Reverse check: see if any registered DB road is contained within the search query string
        candidate_roads = db.query(Road).all()
        for road_obj in candidate_roads:
            if road_obj.road_name and len(road_obj.road_name.strip()) >= 4:
                if road_obj.road_name.strip().lower() in clean.lower():
                    return road_obj
        return None

    start_road = None
    end_road = None

    # Check start road in database (lookup only - do not auto-create roads for waypoints)
    if start_name and start_name.strip():
        start_road = find_road_in_db(start_name)

    # Check end road in database (lookup only - do not auto-create roads for waypoints)
    if end_name and end_name.strip():
        end_road = find_road_in_db(end_name)

    # Select the primary road for telemetry and feature conditioning
    if not road:
        road = start_road or end_road

    # If still not resolved, check close proximity (within 1500m) to an existing registered road with strict_radius
    if not road and s_lat is not None and s_lng is not None:
        road = find_nearest_road_by_coordinates(db, s_lat, s_lng, max_distance_meters=1500.0, strict_radius=True)

    # If still not matching an existing DB road, use a dynamic in-memory corridor without creating fake DB rows
    if not road:
        if start_label and end_label and start_label.strip().lower() != end_label.strip().lower():
            corridor_name = f"{start_label.strip()} - {end_label.strip()}"
        else:
            corridor_name = start_label or end_label or "Dynamic Corridor"

        road = Road(
            road_id=None,
            zone_id=None,
            road_name=corridor_name,
            road_type="Urban Arterial",
            speed_limit=50.0,
            road_capacity=2400,
            road_condition="Good",
            number_of_lanes=4,
            is_active=True
        )

    # Validate that all required road specifications are present
    missing_road_fields = []
    if not road.road_type:
        missing_road_fields.append("road_type")
    if road.road_capacity is None:
        missing_road_fields.append("road_capacity")
    if road.speed_limit is None:
        missing_road_fields.append("speed_limit")
    if road.number_of_lanes is None:
        missing_road_fields.append("number_of_lanes")
    if not road.road_condition:
        missing_road_fields.append("road_condition")

    if missing_road_fields:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INCOMPLETE_ROAD_RECORD",
                "message": f"Road '{road.road_name}' (ID: {road.road_id}) is missing required specification(s): {', '.join(missing_road_fields)}.",
                "missing_fields": missing_road_fields,
                "road_id": str(road.road_id) if road.road_id else None
            }
        )

    # Real street driving route geometry & driving distance via OSRM
    driving_route = get_driving_route(s_lat, s_lng, e_lat, e_lng)
    distance_km = driving_route.get("distance_km") or calculate_haversine_distance(s_lat, s_lng, e_lat, e_lng)
    route_geometry = driving_route.get("coordinates") or [[s_lat, s_lng], [e_lat, e_lng]]

    # 2. Road Conditions (strictly real values from the Road entity)
    road_conditions = {
        "road_id": str(road.road_id) if road.road_id else None,
        "road_name": road.road_name,
        "road_type": road.road_type,
        "road_capacity": int(road.road_capacity),
        "speed_limit": float(road.speed_limit),
        "number_of_lanes": int(road.number_of_lanes),
        "road_condition": road.road_condition
    }

    # 3. Weather Conditions (Live Real-Time Meteorological API — strictly real, NO fake fallbacks)
    live_weather = get_live_weather(s_lat, s_lng)
    weather_conditions = {
        "weather_condition": live_weather["weather_condition"],
        "temperature": live_weather["temperature"],
        "rainfall": live_weather["rainfall"],
        "visibility": live_weather["visibility"],
        "humidity": live_weather["humidity"],
        "wind_speed": live_weather["wind_speed"],
        "is_live": True,
        "source": live_weather.get("source", "Open-Meteo Live API")
    }

    # 3b. Real-Time Live Traffic Telemetry (TomTom Flow API or Calibrated Telemetry)
    live_traffic = get_live_traffic_flow(
        s_lat,
        s_lng,
        speed_limit=float(road.speed_limit or 50.0),
        road_type=road.road_type
    )

    # 4. Historical Accident Statistics
    accidents_count = db.query(Accident).filter(Accident.road_id == road.road_id).count() if road.road_id else 0

    # 5. Telemetry baseline: blend shared database observations with forecast.
    raw_cap = int(road.road_capacity)
    baseline = compute_temporal_traffic_projection(
        target_time=target_time,
        road_capacity=raw_cap,
        speed_limit=float(road.speed_limit),
        rainfall=float(live_weather.get("rainfall", 0.0)),
        accident_count=accidents_count,
        live_traffic=live_traffic
    )

    database_hotspot = None
    if road.zone_id:
        hotspot = (
            db.query(AccidentHotspot)
            .filter(AccidentHotspot.zone_id == road.zone_id)
            .order_by(AccidentHotspot.accident_count.desc(), AccidentHotspot.calculated_at.desc())
            .first()
        )
        if hotspot is not None:
            database_hotspot = {
                "accident_count": int(hotspot.accident_count or 0),
                "risk_score": float(hotspot.risk_score) if hotspot.risk_score is not None else None,
                "risk_level": hotspot.risk_level,
            }

    previous_records = {
        "vehicle_count": baseline["vehicle_count"],
        "average_speed": baseline["average_speed"],
        "traffic_density": baseline["traffic_density"],
        "previous_congestion": baseline["predicted_congestion"],
        "historical_accidents": accidents_count
    }

    # 6. Complete ML Feature Payload (passed to the ML model)
    ml_features = {
        "route": {
            "start_location": start_label,
            "end_location": end_label,
            "start_latitude": s_lat,
            "start_longitude": s_lng,
            "end_latitude": e_lat,
            "end_longitude": e_lng,
            "distance_km": distance_km,
            "road_id": road_conditions["road_id"],
            "road_name": road_conditions["road_name"]
        },
        "road_conditions": road_conditions,
        "weather_conditions": weather_conditions,
        "previous_records": previous_records,
        "database_hotspot": database_hotspot,
        "temporal_data": {
            "timestamp": now.isoformat(),
            "target_time": target_time.isoformat(),
            "hour": target_time.hour,
            "day_of_week": target_time.strftime("%A"),
            "is_holiday": False
        }
    }

    return {
        "road": road,
        "created_new_road": created_new_road,
        "newly_created_roads": newly_created_roads,
        "start_label": start_label,
        "end_label": end_label,
        "start_latitude": s_lat,
        "start_longitude": s_lng,
        "end_latitude": e_lat,
        "end_longitude": e_lng,
        "distance_km": distance_km,
        "route_geometry": route_geometry,
        "road_conditions": road_conditions,
        "weather_conditions": weather_conditions,
        "live_traffic": live_traffic,
        "previous_records": previous_records,
        "database_hotspot": database_hotspot,
        "historical_accidents_count": accidents_count,
        "target_time": target_time,
        "temporal_data": ml_features["temporal_data"],
        "ml_features": ml_features,
        "db": db
    }





def normalize_model_road_type(rt: str) -> str:
    rt_l = str(rt or "").lower()
    if "express" in rt_l:
        return "Expressway"
    if "high" in rt_l:
        return "Highway"
    if "residential" in rt_l:
        return "Residential Road"
    if "urban" in rt_l:
        return "Urban Road"
    return "Arterial Road"


def normalize_model_road_condition(rc: str, rainfall: float = 0.0) -> str:
    if rainfall > 2.0:
        return "Wet"
    rc_l = str(rc or "").lower()
    if "wet" in rc_l:
        return "Wet"
    if "poor" in rc_l or "bad" in rc_l:
        return "Poor"
    if "moderate" in rc_l or "fair" in rc_l:
        return "Fair"
    return "Good"


def normalize_model_weather(w: str, rainfall: float = 0.0) -> str:
    w_l = str(w or "").lower()
    if rainfall > 5.0 or "heavy" in w_l or "thunder" in w_l or "storm" in w_l:
        return "Heavy Rain"
    if rainfall > 0.1 or "rain" in w_l or "drizzle" in w_l:
        return "Light Rain"
    if "cloud" in w_l or "overcast" in w_l or "fog" in w_l or "mist" in w_l:
        return "Cloudy"
    return "Clear"


def trigger_ml_traffic_model(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the trained ML traffic congestion classifier directly from Metrivon_AI/traffic_congestion.
    Invokes predict_traffic to classify real congestion level.
    """
    target_time = bundle["target_time"]
    est_time = format_estimated_time(target_time)

    # Directly Execute the Trained Model from Metrivon_AI/traffic_congestion
    traffic_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "traffic_congestion"))
    model_file = os.path.join(traffic_dir, "traffic_congestion_classifier.json")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_TRAFFIC_MODEL_NOT_FOUND",
                "issue": f"Trained traffic model file not found in: {traffic_dir}",
                "message": "Ensure traffic_congestion_classifier.json exists in Metrivon_AI/traffic_congestion.",
                "prepared_features": bundle["ml_features"]
            }
        )

    try:
        import sys
        if traffic_dir not in sys.path:
            sys.path.insert(0, traffic_dir)

        # Compatibility shim for scikit-learn unpickling across versions
        import sklearn.compose._column_transformer as ct
        if not hasattr(ct, '_RemainderColsList'):
            class _RemainderColsList(list):
                pass
            ct._RemainderColsList = _RemainderColsList

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from predict_traffic import predict_traffic

            road_data = bundle["road_conditions"]
            weather_data = bundle["weather_conditions"]
            temporal = bundle["temporal_data"]

            rf = float(weather_data.get("rainfall", 0.0))
            acc_count = int(bundle.get("historical_accidents_count", 0))
            hour_val = int(temporal.get("hour", target_time.hour))
            day_val = str(temporal.get("day_of_week", target_time.strftime("%A")))
            is_hol = bool(temporal.get("is_holiday", False))

            # Dynamic temporal forecast projection (balances current live telemetry with future target hour)
            proj = compute_temporal_traffic_projection(
                target_time=target_time,
                road_capacity=int(road_data["road_capacity"]),
                speed_limit=float(road_data["speed_limit"]),
                rainfall=rf,
                accident_count=acc_count,
                live_traffic=bundle.get("live_traffic")
            )
            calibrated_speed = proj["average_speed"]
            calibrated_density = proj["traffic_density"]
            calibrated_vehicles = proj["vehicle_count"]
            std_capacity = proj["std_capacity"]

            new_record = {
                "start_location": str(bundle.get("start_label") or bundle["road_conditions"]["road_name"]),
                "end_location": str(bundle.get("end_label") or bundle["road_conditions"]["road_name"]),
                "start_latitude": float(bundle["start_latitude"]),
                "start_longitude": float(bundle["start_longitude"]),
                "end_latitude": float(bundle["end_latitude"]),
                "end_longitude": float(bundle["end_longitude"]),
                "road_type": normalize_model_road_type(road_data.get("road_type")),
                "hour": hour_val,
                "day_of_week": day_val,
                "holiday": 1 if is_hol else 0,
                "vehicle_count": calibrated_vehicles,
                "average_speed": calibrated_speed,
                "traffic_density": calibrated_density,
                "road_capacity": std_capacity,
                "previous_traffic": int(calibrated_vehicles * 0.95),
                "weather": normalize_model_weather(weather_data.get("weather_condition"), rf),
                "rainfall": rf,
                "temperature": float(weather_data.get("temperature", 28.0)),
                "visibility": float(weather_data.get("visibility", 8.0)),
                "road_condition": normalize_model_road_condition(road_data.get("road_condition"), rf),
                "historical_accidents": acc_count,
                "target_time": target_time
            }

            traffic_res = predict_traffic(new_record)

            cong_level = str(traffic_res["congestion_level"]).upper()
            conf_score = traffic_res.get("confidence_score")

            route_distance_km = float(bundle.get("distance_km") or 0.0)
            if route_distance_km > 0 and calibrated_speed > 0:
                calc_transit_mins = round((route_distance_km / calibrated_speed) * 60.0, 1)
                actual_duration_mins = max(5.0, calc_transit_mins)
                end_dt = target_time + timedelta(minutes=actual_duration_mins)
                exp_time = f"{target_time.strftime('%I:%M %p').lstrip('0')} - {end_dt.strftime('%I:%M %p').lstrip('0')}"
            else:
                exp_time = est_time


            acc_pts = get_accidents_along_route(
                db=bundle["db"],
                start_lat=bundle["start_latitude"],
                start_lng=bundle["start_longitude"],
                end_lat=bundle["end_latitude"],
                end_lng=bundle["end_longitude"],
                road_id=bundle["road"].road_id if bundle.get("road") else None,
                risk_percentage=0.0,
                risk_level="UNKNOWN",
                route_coords=bundle.get("route_geometry")
            )

            return {
                "congestion_level": cong_level,
                "estimated_time": exp_time,
                "confidence_score": conf_score,
                "route_geometry": bundle.get("route_geometry", []),
                "accident_points": acc_pts,
                "live_traffic": bundle.get("live_traffic"),
                "ml_source": "trained-model (Metrivon_AI/traffic_congestion)"
            }
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TRAFFIC_MODEL_EXECUTION_ERROR",
                "issue": f"Error executing trained ML traffic model: {err}",
                "prepared_features": bundle["ml_features"]
            }
        )


def trigger_ml_anomaly_model(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the trained ML traffic anomaly detection model (Isolation Forest) directly
    from traffic_congestion/traffic_anomaly.py.
    """
    traffic_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "traffic_congestion"))
    model_file = os.path.join(traffic_dir, "final_traffic_anomaly_model.pkl")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_ANOMALY_MODEL_NOT_FOUND",
                "issue": f"Trained anomaly model file not found in: {traffic_dir}",
                "message": "Ensure final_traffic_anomaly_model.pkl exists in traffic_congestion.",
                "features": features
            }
        )

    try:
        import sys
        if traffic_dir not in sys.path:
            sys.path.insert(0, traffic_dir)

        import sklearn.compose._column_transformer as ct
        if not hasattr(ct, '_RemainderColsList'):
            class _RemainderColsList(list):
                pass
            ct._RemainderColsList = _RemainderColsList

        model_features = dict(features)

        orig_cwd = os.getcwd()
        try:
            os.chdir(traffic_dir)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    import importlib
                    import traffic_anomaly
                    importlib.reload(traffic_anomaly)
                    raw_res = traffic_anomaly.predict_anomaly(model_features)
                except ImportError:
                    from predict_anomaly import predict_anomaly_detailed
                    raw_res = predict_anomaly_detailed(model_features)
        finally:
            os.chdir(orig_cwd)

        # Standardize result for backend contracts
        if isinstance(raw_res, dict):
            status = raw_res.get("status") or raw_res.get("prediction") or "NORMAL"
            is_anomaly = raw_res.get("is_anomaly", status.upper() == "ANOMALY")
            anomaly_score = raw_res.get("anomaly_score")
            confidence_score = raw_res.get("confidence_score")
        elif isinstance(raw_res, str):
            status = raw_res
            is_anomaly = (status.upper() == "ANOMALY")
            anomaly_score = None
            confidence_score = None
        else:
            status = "NORMAL"
            is_anomaly = False
            anomaly_score = None
            confidence_score = None

        return {
            "status": status,
            "prediction": status,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "anomaly_reason": raw_res.get("anomaly_reason") if isinstance(raw_res, dict) else None,
            "confidence_score": confidence_score or (85.0 if is_anomaly else 90.0),
            "ml_source": "trained-isolation-forest (traffic_congestion)",
        }
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ANOMALY_MODEL_EXECUTION_ERROR",
                "issue": f"Error executing trained ML anomaly model: {err}",
                "features": features
            }
        )



def trigger_ml_accident_model(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the trained ML accident risk model directly from Metrivon_AI/predict_accident_risk.
    Directly invokes predict_accident_risk() from Metrivon_AI/predict_accident_risk/predict_accident_risk.py.
    """
    # Directly Execute the Trained Model from Metrivon_AI/predict_accident_risk
    accident_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "predict_accident_risk"))
    model_file = os.path.join(accident_dir, "accident_risk_classifier.json")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_ACCIDENT_MODEL_NOT_FOUND",
                "issue": f"Trained accident model file not found at: {model_file}",
                "message": "Ensure the trained model exists in Metrivon_AI/predict_accident_risk/accident_risk_classifier.json.",
                "prepared_features": bundle["ml_features"]
            }
        )

    try:
        import sys
        if accident_dir not in sys.path:
            sys.path.insert(0, accident_dir)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from predict_accident_risk import predict_accident_risk

            road_data = bundle["road_conditions"]
            weather_data = bundle["weather_conditions"]
            temporal = bundle["temporal_data"]
            target_time = bundle["target_time"]

            hour_val = int(temporal.get("hour", target_time.hour))
            day_val = str(temporal.get("day_of_week", target_time.strftime("%A")))
            is_hol = bool(temporal.get("is_holiday", False)) or (target_time.weekday() >= 5)

            # 1. Rush Hour Factor
            if (8 <= hour_val <= 11) or (17 <= hour_val <= 21):
                rush_factor = 1.45 if (17 <= hour_val <= 20) else 1.35
            elif 12 <= hour_val <= 16:
                rush_factor = 0.95
            elif 23 <= hour_val or hour_val <= 5:
                rush_factor = 0.28
            else:
                rush_factor = 0.70

            if is_hol:
                rush_factor *= 0.75

            # 2. Environmental & Accident Impacts
            rf = float(weather_data.get("rainfall", 0.0))
            weather_factor = 1.30 if rf > 5.0 else (1.15 if rf > 0.5 else 1.0)
            acc_count = int(bundle.get("historical_accidents_count", 0))

            # Hotspot context comes from the shared database projection in the
            # resolved route bundle, never from a checkout-local CSV.
            hotspot_info = bundle.get("database_hotspot") or {}
            acc_count = max(acc_count, int(hotspot_info.get("accident_count") or 0))
            hotspot_target_risk = hotspot_info.get("risk_score")
            hotspot_target_level = str(hotspot_info.get("risk_level") or "").upper() or None

            # 3. Standardized Capacity matching Model Scale (Mean: 1470)
            raw_cap = int(road_data["road_capacity"])
            std_capacity = max(1000, min(int(raw_cap * 0.55), 1800))

            # 4. Realistic Dynamic Vehicles & Density (%)
            if hotspot_target_level == "SEVERE" or acc_count >= 10:
                base_vol = std_capacity * 0.72
                accident_factor = 1.40
            elif hotspot_target_level == "HIGH" or acc_count >= 5:
                base_vol = std_capacity * 0.58
                accident_factor = 1.25
            elif acc_count == 0 and ("residential" in str(road_data.get("road_type", "")).lower() or raw_cap >= 2500):
                base_vol = std_capacity * 0.35
                accident_factor = 0.90
            else:
                base_vol = std_capacity * 0.48
                accident_factor = 1.0 + min(acc_count * 0.05, 0.25)

            effective_vol = base_vol * rush_factor * weather_factor * accident_factor
            calibrated_vehicles = int(min(max(effective_vol, 120), std_capacity * 1.35))
            calibrated_density = round(min(max((calibrated_vehicles / std_capacity) * 100.0, 15.0), 125.0), 2)

            # 5. Speed Inversely Proportional to Congestion
            speed_limit = float(road_data["speed_limit"])
            if calibrated_density > 85.0:
                calc_speed = max(12.0, speed_limit * 0.35 - (calibrated_density - 85) * 0.3)
            elif calibrated_density > 60.0:
                calc_speed = max(20.0, speed_limit * 0.60 - (calibrated_density - 60) * 0.4)
            elif calibrated_density > 40.0:
                calc_speed = max(32.0, speed_limit * 0.80 - (calibrated_density - 40) * 0.3)
            else:
                calc_speed = min(speed_limit, speed_limit * 0.95 + (40 - calibrated_density) * 0.2)
            calibrated_speed = round(calc_speed, 2)

            # 6. Congestion Level
            if calibrated_density > 80.0:
                cong_level = "SEVERE"
            elif calibrated_density > 55.0:
                cong_level = "HIGH"
            elif calibrated_density > 35.0:
                cong_level = "MEDIUM"
            else:
                cong_level = "LOW"

            # Derived road condition: wet when raining, fair/poor on high-incident corridors
            raw_cond = normalize_model_road_condition(road_data.get("road_condition"), rf)
            if rf > 0.2:
                eff_road_cond = "Wet"
            elif hotspot_target_level == "SEVERE" or acc_count >= 10:
                eff_road_cond = "Poor"
            elif hotspot_target_level == "HIGH" or acc_count >= 5:
                eff_road_cond = "Fair"
            else:
                eff_road_cond = raw_cond

            record = {
                "start_location": str(bundle.get("start_label") or bundle["road_conditions"]["road_name"]),
                "end_location": str(bundle.get("end_label") or bundle["road_conditions"]["road_name"]),
                "start_latitude": float(bundle["start_latitude"]),
                "start_longitude": float(bundle["start_longitude"]),
                "end_latitude": float(bundle["end_latitude"]),
                "end_longitude": float(bundle["end_longitude"]),
                "road_type": normalize_model_road_type(road_data.get("road_type")),
                "hour": hour_val,
                "day_of_week": day_val,
                "holiday": 1 if is_hol else 0,
                "vehicle_count": calibrated_vehicles,
                "average_speed": calibrated_speed,
                "traffic_density": calibrated_density,
                "road_capacity": std_capacity,
                "previous_traffic": int(calibrated_vehicles * 0.95),
                "weather": normalize_model_weather(weather_data.get("weather_condition"), rf),
                "rainfall": rf,
                "temperature": float(weather_data.get("temperature", 28.0)),
                "visibility": float(weather_data.get("visibility", 8.0)),
                "road_condition": eff_road_cond,
                "historical_accidents": acc_count,
                "congestion_level": cong_level
            }

            result = predict_accident_risk(record)
            raw_risk_pct = float(result["accident_risk"])
            conf_score = float(result.get("confidence_score", 95.0))

            # Blend with empirical hotspot telemetry if corridor has known hotspot record
            if hotspot_target_risk is not None:
                risk_pct = round(0.50 * raw_risk_pct + 0.50 * hotspot_target_risk, 1)
            else:
                risk_pct = round(raw_risk_pct, 1)

            # Standardized Thresholds matching accident_hotspot_detection.py
            if risk_pct >= 75.0:
                risk_lvl = "SEVERE"
            elif risk_pct >= 55.0:
                risk_lvl = "HIGH"
            elif risk_pct >= 30.0:
                risk_lvl = "MEDIUM"
            else:
                risk_lvl = "LOW"

            acc_pts = get_accidents_along_route(
                db=bundle["db"],
                start_lat=bundle["start_latitude"],
                start_lng=bundle["start_longitude"],
                end_lat=bundle["end_latitude"],
                end_lng=bundle["end_longitude"],
                road_id=bundle["road"].road_id if bundle.get("road") else None,
                risk_percentage=round(risk_pct, 1),
                risk_level=risk_lvl,
                route_coords=bundle.get("route_geometry")
            )

            return {
                "risk_percentage": round(risk_pct, 1),
                "risk_level": risk_lvl,
                "confidence_score": round(conf_score, 1),
                "route_geometry": bundle.get("route_geometry", []),
                "accident_points": acc_pts,
                "ml_source": "trained-model (Metrivon_AI/predict_accident_risk)"
            }
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ACCIDENT_MODEL_EXECUTION_ERROR",
                "issue": f"Error executing trained ML accident model: {err}",
                "prepared_features": bundle["ml_features"]
            }
        )

