import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from app.database.models import Accident, Road, TrafficRecord
from app.services.weather import get_live_weather

logger = logging.getLogger("roadsense.accident_risk_features")


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

    def _get_latest_traffic(self, db: Session, road_id: UUID) -> TrafficRecord:
        record = (
            db.query(TrafficRecord)
            .filter(TrafficRecord.road_id == road_id)
            .order_by(TrafficRecord.timestamp.desc())
            .first()
        )
        if record is None:
            raise ValueError(f"No traffic_records row exists for road_id '{road_id}'. Cannot derive traffic features.")
        return record

    def _get_previous_traffic_count(self, db: Session, road_id: UUID, current_record: TrafficRecord) -> int:
        previous = (
            db.query(TrafficRecord)
            .filter(TrafficRecord.road_id == road_id)
            .filter(TrafficRecord.traffic_id != current_record.traffic_id)
            .filter(TrafficRecord.timestamp < current_record.timestamp)
            .order_by(TrafficRecord.timestamp.desc())
            .first()
        )
        if previous is None:
            return int(current_record.vehicle_count)
        return int(previous.vehicle_count)

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

        traffic_record = self._get_latest_traffic(db, road_id)

        vehicle_count = self._require(traffic_record.vehicle_count, "vehicle_count", road_name)
        average_speed = self._require(traffic_record.average_speed, "average_speed", road_name)
        traffic_density = self._require(traffic_record.traffic_density, "traffic_density", road_name)
        congestion_level = self._require(traffic_record.congestion_level, "congestion_level", road_name)

        if prediction_time is None:
            prediction_time = traffic_record.timestamp or datetime.utcnow()

        weather = self._get_weather(start_lat, start_lon, road_name)
        rainfall = self._require(weather.get("rainfall"), "rainfall", road_name)
        temperature = self._require(weather.get("temperature"), "temperature", road_name)
        visibility = self._require(weather.get("visibility"), "visibility", road_name)
        weather_name = self._require(weather.get("weather_condition"), "weather", road_name)

        historical_accidents = (
            db.query(Accident)
            .filter(Accident.road_id == road_id)
            .count()
        )

        from app.ml.prediction_engine import (
            match_known_location,
            normalize_model_road_type,
            normalize_model_road_condition,
            normalize_model_weather,
            KNOWN_START_LOCS,
            KNOWN_END_LOCS,
        )

        hour_val = int(prediction_time.hour)
        day_val = prediction_time.strftime("%A")
        is_hol = 1 if (traffic_record.is_holiday is True or prediction_time.weekday() >= 5) else 0

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

        # 2. Environmental & Accident Factors
        rf = float(rainfall)
        weather_factor = 1.30 if rf > 5.0 else (1.15 if rf > 0.5 else 1.0)
        accident_factor = 1.0 + min(historical_accidents * 0.05, 0.35)

        # 3. Standardized Capacity matching Model Scale (Mean: 1470)
        raw_cap = int(road_capacity or 1500)
        std_capacity = max(1000, min(int(raw_cap * 0.55), 1800))

        # 4. Realistic Dynamic Density & Vehicles
        base_vol = std_capacity * 0.50
        effective_vol = base_vol * rush_factor * weather_factor * accident_factor
        calibrated_vehicles = int(min(max(effective_vol, 120), std_capacity * 1.35))
        calibrated_density = round(min(max((calibrated_vehicles / std_capacity) * 100.0, 15.0), 125.0), 2)

        # 5. Speed Inversely Proportional to Congestion
        speed_limit = float(road.speed_limit or 50.0)
        if calibrated_density > 85.0:
            calc_speed = max(12.0, speed_limit * 0.35 - (calibrated_density - 85) * 0.3)
        elif calibrated_density > 60.0:
            calc_speed = max(20.0, speed_limit * 0.60 - (calibrated_density - 60) * 0.4)
        elif calibrated_density > 40.0:
            calc_speed = max(32.0, speed_limit * 0.80 - (calibrated_density - 40) * 0.3)
        else:
            calc_speed = min(speed_limit, speed_limit * 0.95 + (40 - calibrated_density) * 0.2)
        calibrated_speed = round(calc_speed, 2)

        # 6. Congestion Level Mapping
        if calibrated_density > 80.0:
            cong_level = "SEVERE"
        elif calibrated_density > 55.0:
            cong_level = "HIGH"
        elif calibrated_density > 35.0:
            cong_level = "MEDIUM"
        else:
            cong_level = "LOW"

        payload = {
            "start_location": match_known_location(road_name, KNOWN_START_LOCS),
            "end_location": match_known_location(road_name, KNOWN_END_LOCS),
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
