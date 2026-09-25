import os
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from fastapi import HTTPException
from app.database.models import Road, Accident
from app.services.geocoding import (
    geocode_location,
    reverse_geocode,
    find_nearest_road_by_coordinates,
    get_driving_route,
    get_accidents_along_route
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
      real-time TomTom sensor telemetry using a temporal decay window.
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
    if live_traffic and live_traffic.get("is_live") and live_traffic.get("current_speed_kmh"):
        w_live = max(0.0, min(1.0, 1.0 - (delta_mins / 60.0)))
        live_speed = float(live_traffic["current_speed_kmh"])
        slowdown_pct = float(live_traffic.get("slowdown_percentage", 0.0))
        live_density = round(min(120.0, max(15.0, 28.0 + (slowdown_pct * 0.85))), 2)
        live_vehicles = max(150, int(std_capacity * (live_density / 100.0)))

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

    # 2. Resolve real latitude & longitude
    s_lat = start_lat
    s_lng = start_lng
    e_lat = end_lat
    e_lng = end_lng

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
            geo_results = geocode_location(start_name)
            if geo_results:
                s_lat = geo_results[0]["latitude"]
                s_lng = geo_results[0]["longitude"]

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
            geo_results = geocode_location(end_name)
            if geo_results:
                e_lat = geo_results[0]["latitude"]
                e_lng = geo_results[0]["longitude"]

    # Strict check: Start and destination coordinates must be provided and resolvable
    if s_lat is None or s_lng is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "MISSING_START_COORDINATES",
                "message": f"Start coordinates could not be resolved for '{start_name or 'unspecified'}'. Please specify a valid origin location or exact latitude/longitude.",
                "field": "start_location"
            }
        )

    if e_lat is None or e_lng is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "MISSING_END_COORDINATES",
                "message": f"Destination coordinates could not be resolved for '{end_name or 'unspecified'}'. Please specify a valid destination location or exact latitude/longitude.",
                "field": "end_location"
            }
        )

    # Reverse geocode labels if user only passed coordinates (e.g. Map Click or GPS)
    start_label = start_name
    if not start_label:
        rev = reverse_geocode(s_lat, s_lng)
        if rev:
            start_label = rev.get("road") or rev.get("suburb") or rev.get("neighbourhood") or rev.get("display_name")
    if not start_label:
        start_label = f"Location [{s_lat:.4f}, {s_lng:.4f}]"

    end_label = end_name
    if not end_label:
        rev = reverse_geocode(e_lat, e_lng)
        if rev:
            end_label = rev.get("road") or rev.get("suburb") or rev.get("neighbourhood") or rev.get("display_name")
    if not end_label:
        end_label = f"Location [{e_lat:.4f}, {e_lng:.4f}]"

    # 3. Match or locate Road entity strictly from the database if not yet resolved
    if not road and s_lat is not None and s_lng is not None:
        road = find_nearest_road_by_coordinates(db, s_lat, s_lng)

    if not road and (start_label or end_label):
        search_term = start_label or end_label
        road = db.query(Road).filter(Road.road_name.ilike(f"%{search_term}%")).first()

    if not road:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "ROAD_NOT_FOUND",
                "message": f"No registered road found in the database near route from '{start_label}' to '{end_label}' (Coordinates: [{s_lat}, {s_lng}] -> [{e_lat}, {e_lng}]). Defaults are disabled; please register this road corridor in the database first.",
                "coordinates": {"start": [s_lat, s_lng], "end": [e_lat, e_lng]}
            }
        )

    # Validate that all required road specifications are present in the database
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
                "message": f"Road '{road.road_name}' (ID: {road.road_id}) is missing required specification(s): {', '.join(missing_road_fields)}. Defaults are disabled; please update this road in the database with complete attributes.",
                "missing_fields": missing_road_fields,
                "road_id": str(road.road_id)
            }
        )

    # Real street driving route geometry & driving distance via OSRM
    driving_route = get_driving_route(s_lat, s_lng, e_lat, e_lng)
    distance_km = driving_route.get("distance_km") or calculate_haversine_distance(s_lat, s_lng, e_lat, e_lng)
    route_geometry = driving_route.get("coordinates") or [[s_lat, s_lng], [e_lat, e_lng]]

    # 2. Road Conditions (strictly real values from the Road entity)
    road_conditions = {
        "road_id": str(road.road_id),
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
    accidents_count = db.query(Accident).filter(Accident.road_id == road.road_id).count()

    # 5. Telemetry Baseline: Dynamic blend between real-time TomTom telemetry (near-term) and temporal forecast (future)
    raw_cap = int(road.road_capacity or 1500)
    baseline = compute_temporal_traffic_projection(
        target_time=target_time,
        road_capacity=raw_cap,
        speed_limit=float(road.speed_limit or 50.0),
        rainfall=float(live_weather.get("rainfall", 0.0)),
        accident_count=accidents_count,
        live_traffic=live_traffic
    )

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
    Executes the trained ML traffic congestion model directly from RoadSense_AI/traffic_congestion.
    Invokes predict_traffic and predict_expected_congestion_time.
    """
    target_time = bundle["target_time"]
    est_time = format_estimated_time(target_time)

    # Directly Execute the Trained Model from RoadSense_AI/traffic_congestion
    traffic_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "traffic_congestion"))
    model_file = os.path.join(traffic_dir, "traffic_congestion_classifier.json")
    time_model_file = os.path.join(traffic_dir, "expected_congestion_time_regressor.json")

    if not os.path.exists(model_file) or not os.path.exists(time_model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_TRAFFIC_MODEL_NOT_FOUND",
                "issue": f"Trained traffic model file not found in: {traffic_dir}",
                "message": "Ensure the updated trained model files exist in RoadSense_AI/traffic_congestion.",
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
            from predict_expected_congestion_time import predict_expected_congestion_time

            road_data = bundle["road_conditions"]
            weather_data = bundle["weather_conditions"]
            prev_data = bundle["previous_records"]
            temporal = bundle["temporal_data"]

            rf = float(weather_data.get("rainfall", 0.0))
            acc_count = int(bundle.get("historical_accidents_count", 0))
            hour_val = int(temporal.get("hour", target_time.hour))
            day_val = str(temporal.get("day_of_week", target_time.strftime("%A")))
            is_hol = bool(temporal.get("is_holiday", False))

            # Dynamic temporal forecast projection (balances current live telemetry with future target hour)
            proj = compute_temporal_traffic_projection(
                target_time=target_time,
                road_capacity=int(road_data.get("road_capacity") or 1500),
                speed_limit=float(road_data.get("speed_limit") or 50.0),
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
            time_res = predict_expected_congestion_time(new_record)

            cong_level = str(traffic_res["congestion_level"]).upper()
            conf_score = traffic_res.get("confidence_score")

            # Route distance scaling:
            # The standalone ML regressor was trained on fixed junction segments (~6.5 km).
            # For full routes (e.g. 23 km), traveling duration must scale with actual distance
            # and congestion-adjusted speed (Distance / Speed * 60):
            route_distance_km = float(bundle.get("distance_km") or 0.0)
            if route_distance_km > 0 and calibrated_speed > 0:
                calc_transit_mins = round((route_distance_km / calibrated_speed) * 60.0, 1)
                actual_duration_mins = max(5.0, calc_transit_mins)
                end_dt = target_time + timedelta(minutes=actual_duration_mins)
                exp_time = f"{target_time.strftime('%I:%M %p').lstrip('0')} - {end_dt.strftime('%I:%M %p').lstrip('0')}"
            else:
                exp_time = time_res.get("expected_congestion_period") or est_time

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
                "ml_source": "trained-model (RoadSense_AI/traffic_congestion)"
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


def trigger_ml_accident_model(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the trained ML accident risk model directly from RoadSense_AI/predict_accident_risk.
    Directly invokes predict_accident_risk() from RoadSense_AI/predict_accident_risk/predict_accident_risk.py.
    """
    # Directly Execute the Trained Model from RoadSense_AI/predict_accident_risk
    accident_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "predict_accident_risk"))
    model_file = os.path.join(accident_dir, "accident_risk_classifier.json")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_ACCIDENT_MODEL_NOT_FOUND",
                "issue": f"Trained accident model file not found at: {model_file}",
                "message": "Ensure the trained model exists in RoadSense_AI/predict_accident_risk/accident_risk_classifier.json.",
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

            # Check if this corridor matches an empirical accident hotspot from accident_hotspots.csv
            hotspot_info = None
            hotspot_csv = os.path.join(accident_dir, "accident_hotspots.csv")
            s_raw = str(bundle.get("start_label", "")).lower()
            e_raw = str(bundle.get("end_label", "")).lower()

            if os.path.exists(hotspot_csv):
                try:
                    import pandas as pd
                    hs_df = pd.read_csv(hotspot_csv)
                    m = hs_df[
                        hs_df["start_location"].str.lower().apply(lambda x: x in s_raw or s_raw in x) &
                        hs_df["end_location"].str.lower().apply(lambda x: x in e_raw or e_raw in x)
                    ]
                    if not m.empty:
                        hotspot_info = m.iloc[0]
                except Exception:
                    pass

            if hotspot_info is not None:
                acc_count = max(acc_count, int(hotspot_info.get("accidents", 0)))
                hotspot_target_risk = float(hotspot_info.get("average_risk", 50.0))
                hotspot_target_level = str(hotspot_info.get("risk", "MEDIUM")).upper()
            else:
                hotspot_target_risk = None
                hotspot_target_level = None

            # 3. Standardized Capacity matching Model Scale (Mean: 1470)
            raw_cap = int(road_data.get("road_capacity") or 1500)
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
            speed_limit = float(road_data.get("speed_limit") or 50.0)
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
                "ml_source": "trained-model (RoadSense_AI/predict_accident_risk)"
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


def trigger_ml_anomaly_model(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the trained ML traffic anomaly detection model (Isolation Forest) directly
    from RoadSense_AI/traffic_congestion/predict_anomaly.py.
    """
    traffic_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "traffic_congestion"))
    model_file = os.path.join(traffic_dir, "final_traffic_anomaly_model.pkl")
    if not os.path.exists(model_file):
        model_file = os.path.join(traffic_dir, "model", "final_traffic_anomaly_model.pkl")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_ANOMALY_MODEL_NOT_FOUND",
                "issue": f"Trained anomaly model file not found in: {traffic_dir}",
                "message": "Ensure final_traffic_anomaly_model.pkl exists in RoadSense_AI/traffic_congestion.",
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

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from predict_anomaly import predict_anomaly_detailed

            result = predict_anomaly_detailed(features)
            result["ml_source"] = "trained-isolation-forest (RoadSense_AI/traffic_congestion)"
            return result
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ANOMALY_MODEL_EXECUTION_ERROR",
                "issue": f"Error executing trained ML anomaly model: {err}",
                "features": features
            }
        )

