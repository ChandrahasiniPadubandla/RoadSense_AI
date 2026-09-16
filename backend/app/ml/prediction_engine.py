import os
import math
import json
import urllib.request
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from fastapi import HTTPException
from app.database.models import Road, TrafficRecord, Accident
from app.services.geocoding import (
    geocode_location,
    reverse_geocode,
    find_nearest_road_by_coordinates,
    get_driving_route,
    get_accidents_along_route
)
from app.services.weather import get_live_weather


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

    # Dynamic Geocoding: resolve text queries into real coordinates
    if (s_lat is None or s_lng is None) and start_name:
        geo_results = geocode_location(start_name)
        if geo_results:
            s_lat = geo_results[0]["latitude"]
            s_lng = geo_results[0]["longitude"]

    if (e_lat is None or e_lng is None) and end_name:
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

    # 4. Previous Records (strictly from recorded traffic data for this road)
    traffic = (
        db.query(TrafficRecord)
        .filter(TrafficRecord.road_id == road.road_id)
        .order_by(TrafficRecord.timestamp.desc())
        .first()
    )

    if not traffic:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "NO_TRAFFIC_RECORDS",
                "message": f"No traffic records found in the database for road '{road.road_name}' (ID: {road.road_id}). Defaults are disabled; real recorded traffic data is required for prediction.",
                "road_id": str(road.road_id),
                "road_name": road.road_name
            }
        )

    missing_traffic_fields = []
    if traffic.vehicle_count is None:
        missing_traffic_fields.append("vehicle_count")
    if traffic.average_speed is None:
        missing_traffic_fields.append("average_speed")
    if traffic.traffic_density is None:
        missing_traffic_fields.append("traffic_density")
    if not traffic.congestion_level:
        missing_traffic_fields.append("congestion_level")

    if missing_traffic_fields:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INCOMPLETE_TRAFFIC_RECORD",
                "message": f"Latest traffic record for road '{road.road_name}' is missing required field(s): {', '.join(missing_traffic_fields)}. Defaults are disabled; real recorded data is required.",
                "missing_fields": missing_traffic_fields,
                "road_id": str(road.road_id)
            }
        )

    # 5. Historical Accident Statistics
    accidents_count = db.query(Accident).filter(Accident.road_id == road.road_id).count()

    previous_records = {
        "vehicle_count": int(traffic.vehicle_count),
        "average_speed": float(traffic.average_speed),
        "traffic_density": float(traffic.traffic_density),
        "previous_congestion": traffic.congestion_level,
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
        "previous_records": previous_records,
        "historical_accidents_count": accidents_count,
        "target_time": target_time,
        "temporal_data": ml_features["temporal_data"],
        "ml_features": ml_features,
        "db": db
    }


def trigger_ml_traffic_model(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the trained ML traffic congestion model directly from RoadSense_AI/ML.
    If external ML endpoint (ML_TRAFFIC_SERVICE_URL) is set, routes via HTTP POST.
    Otherwise, directly invokes predict_congestion() from RoadSense_AI/ML/prediction/predict_traffic_congesion.py.
    """
    ml_url = os.getenv("ML_TRAFFIC_SERVICE_URL", "").strip()
    target_time = bundle["target_time"]
    est_time = format_estimated_time(target_time)

    # 1. External Microservice (if configured)
    if ml_url:
        try:
            req_data = json.dumps(bundle["ml_features"]).encode("utf-8")
            req = urllib.request.Request(
                ml_url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                cong = result.get("congestion_level") or result.get("predicted_congestion")
                if not cong:
                    raise HTTPException(
                        status_code=502,
                        detail={
                            "error": "ML_MODEL_INVALID_RESPONSE",
                            "issue": f"ML model at {ml_url} did not return 'congestion_level'.",
                            "received_response": result
                        }
                    )
                return {
                    "congestion_level": str(cong).upper(),
                    "estimated_time": result.get("estimated_time") or est_time,
                    "confidence_score": float(result.get("confidence_score")) if result.get("confidence_score") is not None else None,
                    "ml_source": "external-ml-model"
                }
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "ML_TRAFFIC_MODEL_UNAVAILABLE",
                    "issue": f"Failed to connect to ML Traffic Model at '{ml_url}'.",
                    "technical_details": str(err),
                    "message": "Could not reach external ML Traffic Model. Ensure the ML service is running.",
                    "prepared_features": bundle["ml_features"]
                }
            )

    # 2. Directly Execute the Trained Model from RoadSense_AI/ML
    ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ML"))
    model_file = os.path.join(ml_dir, "model", "traffic_congestion_random_forest.pkl")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_TRAFFIC_MODEL_NOT_FOUND",
                "issue": f"Trained traffic model file not found at: {model_file}",
                "message": "Ensure the trained model exists in RoadSense_AI/ML/model/traffic_congestion_random_forest.pkl or set ML_TRAFFIC_SERVICE_URL.",
                "prepared_features": bundle["ml_features"]
            }
        )

    try:
        import sys
        if ml_dir not in sys.path:
            sys.path.insert(0, ml_dir)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from prediction.predict_traffic_congesion import predict_congestion

            road_data = bundle["road_conditions"]
            weather_data = bundle["weather_conditions"]
            prev_data = bundle["previous_records"]
            temporal = bundle["temporal_data"]

            result = predict_congestion(
                road_id=str(road_data["road_id"]),
                location=str(bundle["start_label"]),
                latitude=float(bundle["start_latitude"]),
                longitude=float(bundle["start_longitude"]),
                road_type=str(road_data["road_type"]),
                hour=int(temporal["hour"]),
                day_of_week=str(temporal["day_of_week"]),
                holiday=1 if temporal.get("is_holiday") else 0,
                vehicle_count=int(prev_data["vehicle_count"]),
                average_speed=float(prev_data["average_speed"]),
                traffic_density=float(prev_data["traffic_density"]),
                road_capacity=int(road_data["road_capacity"]),
                previous_traffic=int(prev_data["vehicle_count"]),
                weather=str(weather_data["weather_condition"]),
                rainfall=float(weather_data["rainfall"]),
                temperature=float(weather_data["temperature"]),
                visibility=float(weather_data["visibility"]),
                road_condition=str(road_data["road_condition"]),
                historical_accidents=int(bundle["historical_accidents_count"])
            )

            cong_level = str(result["predicted_congestion"]).upper()
            exp_time = result.get("expected_congestion_time") or est_time

            # Compute actual confidence from the trained model probabilities
            conf_score = None
            try:
                import pandas as pd
                from prediction.predict_traffic_congesion import model as tf_model
                if hasattr(tf_model, "predict_proba"):
                    new_df = pd.DataFrame([{
                        "road_id": str(road_data["road_id"]),
                        "location": str(bundle["start_label"]),
                        "latitude": float(bundle["start_latitude"]),
                        "longitude": float(bundle["start_longitude"]),
                        "road_type": str(road_data["road_type"]),
                        "hour": int(temporal["hour"]),
                        "day_of_week": str(temporal["day_of_week"]),
                        "holiday": 1 if temporal.get("is_holiday") else 0,
                        "vehicle_count": int(prev_data["vehicle_count"]),
                        "average_speed": float(prev_data["average_speed"]),
                        "traffic_density": float(prev_data["traffic_density"]),
                        "road_capacity": int(road_data["road_capacity"]),
                        "previous_traffic": int(prev_data["vehicle_count"]),
                        "weather": str(weather_data["weather_condition"]),
                        "rainfall": float(weather_data["rainfall"]),
                        "temperature": float(weather_data["temperature"]),
                        "visibility": float(weather_data["visibility"]),
                        "road_condition": str(road_data["road_condition"]),
                        "historical_accidents": int(bundle["historical_accidents_count"])
                    }])
                    probs = tf_model.predict_proba(new_df)[0]
                    conf_score = round(float(max(probs)) * 100.0, 1)
            except Exception:
                conf_score = None

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
                "ml_source": "trained-model (RoadSense_AI/ML/model/traffic_congestion_random_forest.pkl)"
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
    Executes the trained ML accident risk model directly from RoadSense_AI/ML.
    If external ML endpoint (ML_ACCIDENT_SERVICE_URL) is set, routes via HTTP POST.
    Otherwise, directly invokes predict_record() from RoadSense_AI/ML/prediction/predict_accident_risk.py.
    """
    ml_url = os.getenv("ML_ACCIDENT_SERVICE_URL", "").strip()

    # 1. External Microservice (if configured)
    if ml_url:
        try:
            req_data = json.dumps(bundle["ml_features"]).encode("utf-8")
            req = urllib.request.Request(
                ml_url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                risk_pct = result.get("risk_percentage")
                risk_lvl = result.get("risk_level")
                if risk_pct is None or not risk_lvl:
                    raise HTTPException(
                        status_code=502,
                        detail={
                            "error": "ML_MODEL_INVALID_RESPONSE",
                            "issue": f"ML model at {ml_url} did not return 'risk_percentage' and 'risk_level'.",
                            "received_response": result
                        }
                    )
                return {
                    "risk_percentage": round(float(risk_pct), 1),
                    "risk_level": str(risk_lvl).upper(),
                    "confidence_score": float(result.get("confidence_score")) if result.get("confidence_score") is not None else None,
                    "ml_source": "external-ml-model"
                }
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "ML_ACCIDENT_MODEL_UNAVAILABLE",
                    "issue": f"Failed to connect to ML Accident Model at '{ml_url}'.",
                    "technical_details": str(err),
                    "message": "Could not reach external ML Accident Model. Ensure the ML service is running.",
                    "prepared_features": bundle["ml_features"]
                }
            )

    # 2. Directly Execute the Trained Model from RoadSense_AI/ML
    ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ML"))
    model_file = os.path.join(ml_dir, "model", "accident_risk_model.pkl")

    if not os.path.exists(model_file):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ML_ACCIDENT_MODEL_NOT_FOUND",
                "issue": f"Trained accident model file not found at: {model_file}",
                "message": "Ensure the trained model exists in RoadSense_AI/ML/model/accident_risk_model.pkl or set ML_ACCIDENT_SERVICE_URL.",
                "prepared_features": bundle["ml_features"]
            }
        )

    try:
        import sys
        if ml_dir not in sys.path:
            sys.path.insert(0, ml_dir)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from prediction.predict_accident_risk import predict_record

            road_data = bundle["road_conditions"]
            weather_data = bundle["weather_conditions"]
            prev_data = bundle["previous_records"]
            temporal = bundle["temporal_data"]

            # Format categories to uppercase for OneHotEncoder matching
            r_type = str(road_data["road_type"]).upper()
            w_cond = str(weather_data["weather_condition"]).upper()
            rd_cond = str(road_data["road_condition"]).upper()
            day_str = str(temporal["day_of_week"]).upper()
            prev_cong = str(prev_data["previous_congestion"]).upper()

            record = {
                "location": str(bundle["start_label"]),
                "latitude": float(bundle["start_latitude"]),
                "longitude": float(bundle["start_longitude"]),
                "road_type": r_type,
                "hour": int(temporal["hour"]),
                "day_of_week": day_str,
                "holiday": 1 if temporal.get("is_holiday") else 0,
                "vehicle_count": int(prev_data["vehicle_count"]),
                "average_speed": float(prev_data["average_speed"]),
                "traffic_density": float(prev_data["traffic_density"]),
                "road_capacity": int(road_data["road_capacity"]),
                "previous_traffic": int(prev_data["vehicle_count"]),
                "weather": w_cond,
                "rainfall": float(weather_data["rainfall"]),
                "temperature": float(weather_data["temperature"]),
                "visibility": float(weather_data["visibility"]),
                "road_condition": rd_cond,
                "historical_accidents": int(bundle["historical_accidents_count"]),
                "congestion_level": prev_cong
            }

            result = predict_record(record)
            risk_pct = float(result["accident_risk"])
            risk_lvl = str(result["accident_risk_level"]).upper()
            conf_score = round(float(result.get("accident_risk", 0.0)), 1)

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
                "confidence_score": conf_score,
                "route_geometry": bundle.get("route_geometry", []),
                "accident_points": acc_pts,
                "ml_source": "trained-model (RoadSense_AI/ML/model/accident_risk_model.pkl)"
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

