import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from app.database.models import Accident, Road
from app.services.weather import get_live_weather
from app.services.live_traffic import get_live_traffic_flow
from app.ml.prediction_engine import (
    compute_temporal_traffic_projection,
    normalize_model_road_type,
    normalize_model_road_condition,
    normalize_model_weather,
)

logger = logging.getLogger("Metrivon.accident_risk_features")


class AccidentRiskFeatureService:
    REQUIRED_FIELDS = [
        "start_location",
        "end_location",
        "start_latitude",
        "start_longitude",
        "end_latitude",
        "end_longitude",
        "road_type",
        "hour",
        "day_of_week",
        "holiday",
        "vehicle_count",
        "average_speed",
        "traffic_density",
        "road_capacity",
        "previous_traffic",
        "weather",
        "rainfall",
        "temperature",
        "visibility",
        "road_condition",
        "historical_accidents",
        "congestion_level",
    ]

    def _require(self, value: Any, field_name: str, road_name: str) -> Any:
        if value is None or value == "":
            raise ValueError(f"Required prediction field '{field_name}' for road '{road_name}' is missing in the database.")
        return value

    def _read_point(self, geo_value: Any) -> Optional[tuple[float, float]]:
        if geo_value is None:
            return None
        try:
            point = to_shape(geo_value)
            return float(point.y), float(point.x)
        except Exception:
            return None

    def _get_weather(self, latitude: float, longitude: float, road_name: str) -> Dict[str, Any]:
        try:
            return get_live_weather(latitude=latitude, longitude=longitude)
        except Exception as exc:  # pragma: no cover - network/service failure is handled by HTTP layer
            raise ValueError(f"Real weather data unavailable for road '{road_name}' at coordinates ({latitude}, {longitude}): {exc}") from exc

    def _get_road_label(self, road: Road) -> str:
        if road.road_name:
            return road.road_name
        return "Road"

    def build_feature_payload(self, db: Session, road_id: UUID, prediction_time: Optional[datetime] = None) -> Dict[str, Any]:
        road = db.query(Road).filter(Road.road_id == road_id).first()
        if road is None:
            raise ValueError(f"Road with ID '{road_id}' does not exist in the database.")

        road_name = self._get_road_label(road)

        start_point = self._read_point(road.start_location)
        end_point = self._read_point(road.end_location)
        if start_point is None or end_point is None:
            raise ValueError(f"Road '{road_name}' is missing usable start/end coordinates in the database.")

        start_lat, start_lon = start_point
        end_lat, end_lon = end_point

        road_type = self._require(road.road_type, "road_type", road_name)
        road_capacity = self._require(road.road_capacity, "road_capacity", road_name)
        road_condition = self._require(road.road_condition, "road_condition", road_name)
        speed_limit = float(road.speed_limit or 50.0)

        if prediction_time is None:
            prediction_time = datetime.now()

        # 1. Live Meteorological Telemetry (strictly real, NO fake fallbacks)
        weather = self._get_weather(start_lat, start_lon, road_name)
        rainfall = float(self._require(weather.get("rainfall"), "rainfall", road_name))
        temperature = float(self._require(weather.get("temperature"), "temperature", road_name))
        visibility = float(self._require(weather.get("visibility"), "visibility", road_name))
        weather_name = str(self._require(weather.get("weather_condition"), "weather", road_name))

        # 2. Historical Incident Statistics
        historical_accidents = (
            db.query(Accident)
            .filter(Accident.road_id == road_id)
            .count()
        )

        # 3. Live Real-Time Traffic Telemetry (TomTom Flow API)
        live_traffic = get_live_traffic_flow(
            start_lat,
            start_lon,
            speed_limit=speed_limit,
            road_type=road_type
        )

        # 4. Centralized Dynamic Temporal Traffic Projection
        proj = compute_temporal_traffic_projection(
            target_time=prediction_time,
            road_capacity=int(road_capacity or 1500),
            speed_limit=speed_limit,
            rainfall=rainfall,
            accident_count=historical_accidents,
            live_traffic=live_traffic
        )

        hour_val = int(prediction_time.hour)
        day_val = prediction_time.strftime("%A")
        is_hol = 1 if prediction_time.weekday() >= 5 else 0

        calibrated_vehicles = proj["vehicle_count"]
        calibrated_speed = proj["average_speed"]
        calibrated_density = proj["traffic_density"]
        std_capacity = proj["std_capacity"]
        cong_level = proj["predicted_congestion"]
        rf = rainfall

        payload = {
            "start_location": str(road_name),
            "end_location": str(road_name),
            "start_latitude": float(start_lat),
            "start_longitude": float(start_lon),
            "end_latitude": float(end_lat),
            "end_longitude": float(end_lon),
            "road_type": normalize_model_road_type(road_type),
            "hour": hour_val,
            "day_of_week": day_val,
            "holiday": is_hol,
            "vehicle_count": calibrated_vehicles,
            "average_speed": calibrated_speed,
            "traffic_density": calibrated_density,
            "road_capacity": std_capacity,
            "previous_traffic": int(calibrated_vehicles * 0.95),
            "weather": normalize_model_weather(weather_name, rf),
            "rainfall": rf,
            "temperature": float(temperature),
            "visibility": float(visibility),
            "road_condition": normalize_model_road_condition(road_condition, rf),
            "historical_accidents": int(historical_accidents),
            "congestion_level": cong_level,
            "road_id": str(road_id),
            "road_name": road_name,
        }

        missing = [field for field in self.REQUIRED_FIELDS if field not in payload or payload[field] is None or payload[field] == ""]
        if missing:
            raise ValueError(f"Feature preparation for road '{road_name}' is incomplete: {', '.join(missing)}")

        return payload


accident_risk_feature_service = AccidentRiskFeatureService()
