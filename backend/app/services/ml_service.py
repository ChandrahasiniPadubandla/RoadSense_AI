from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import Accident, Road, TrafficAnomaly, TrafficRecord
from app.ml.prediction_engine import resolve_route_bundle, trigger_ml_anomaly_model
from app.schemas.ml import (
    AnomalyPredictionRequest,
    AnomalyPredictionResponse,
)


def _request_or_database_value(request_value, database_value, field_name):
    value = request_value if request_value is not None else database_value
    if value is None:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be provided or available from a shared database traffic record.",
        )
    return value


class MLService:

    def _get_road_record(self, road_id: str) -> Road:
        db: Session = SessionLocal()
        try:
            road = db.query(Road).filter(Road.road_id == road_id).first()
            if road is None:
                raise ValueError(f"Road with ID '{road_id}' does not exist in the database.")
            return road
        finally:
            db.close()

    def _get_latest_traffic(self, road_id: str) -> TrafficRecord:
        db: Session = SessionLocal()
        try:
            record = (
                db.query(TrafficRecord)
                .filter(TrafficRecord.road_id == road_id)
                .order_by(TrafficRecord.timestamp.desc(), TrafficRecord.traffic_id.desc())
                .first()
            )
            if record is None:
                raise ValueError(f"No traffic records exist for road '{road_id}' in the database.")
            return record
        finally:
            db.close()

    def predict_anomaly(
        self,
        request: AnomalyPredictionRequest,
    ) -> AnomalyPredictionResponse:
        road = None
        traffic = None
        road_name = None

        if request.road_id:
            try:
                road = self._get_road_record(request.road_id)
                road_name = road.road_name
                try:
                    traffic = self._get_latest_traffic(str(road.road_id))
                except Exception:
                    traffic = None
            except Exception:
                road = None

        if not road and (request.start_location or request.end_location or request.start_latitude):
            db_bundle = SessionLocal()
            try:
                bundle = resolve_route_bundle(
                    db=db_bundle,
                    start_name=request.start_location,
                    end_name=request.end_location,
                    start_lat=request.start_latitude,
                    start_lng=request.start_longitude,
                    end_lat=request.end_latitude,
                    end_lng=request.end_longitude
                )
                road = bundle.get("road")
                road_name = bundle.get("road_conditions", {}).get("road_name") or bundle.get("start_label")
                prev = bundle.get("previous_records", {})
                r_cond = bundle.get("road_conditions", {})
                if request.vehicle_count is None and prev.get("vehicle_count") is not None:
                    request.vehicle_count = int(prev["vehicle_count"])
                if request.average_speed is None and prev.get("average_speed") is not None:
                    request.average_speed = float(prev["average_speed"])
                if request.traffic_density is None and prev.get("traffic_density") is not None:
                    request.traffic_density = float(prev["traffic_density"])
                if request.previous_traffic is None and prev.get("previous_traffic") is not None:
                    request.previous_traffic = int(prev["previous_traffic"])
                if request.road_capacity is None and r_cond.get("road_capacity") is not None:
                    request.road_capacity = int(r_cond["road_capacity"])
            except Exception:
                pass
            finally:
                db_bundle.close()

        vehicle_count = _request_or_database_value(
            request.vehicle_count,
            traffic.vehicle_count if traffic else None,
            "vehicle_count",
        )
        average_speed = _request_or_database_value(
            request.average_speed,
            traffic.average_speed if traffic else None,
            "average_speed",
        )
        traffic_density = _request_or_database_value(
            request.traffic_density,
            traffic.traffic_density if traffic else None,
            "traffic_density",
        )
        road_capacity = _request_or_database_value(
            request.road_capacity,
            road.road_capacity if road else None,
            "road_capacity",
        )
        previous_traffic = _request_or_database_value(
            request.previous_traffic,
            int(traffic.vehicle_count * 0.95) if traffic and traffic.vehicle_count is not None else None,
            "previous_traffic",
        )

        hour = request.hour
        if hour is None:
            hour = traffic.timestamp.hour if (traffic and traffic.timestamp) else datetime.now(timezone.utc).hour

        historical_accidents = getattr(request, "historical_accidents", None)
        if historical_accidents is None:
            if road and hasattr(road, "historical_accidents") and road.historical_accidents is not None:
                historical_accidents = int(road.historical_accidents)
            elif road:
                db_acc = SessionLocal()
                try:
                    historical_accidents = db_acc.query(Accident).filter(Accident.road_id == road.road_id).count()
                except Exception:
                    historical_accidents = 0
                finally:
                    db_acc.close()
            else:
                historical_accidents = 0

        features = {
            "vehicle_count": vehicle_count,
            "average_speed": average_speed,
            "traffic_density": traffic_density,
            "road_capacity": road_capacity,
            "previous_traffic": previous_traffic,
            "hour": hour,
            "historical_accidents": historical_accidents,
        }

        ml_result = trigger_ml_anomaly_model(features)
        prediction_text = ml_result["prediction"]
        is_anomaly = ml_result["is_anomaly"]

        if request.persist and road:
            db = SessionLocal()
            try:
                anomaly_record = TrafficAnomaly(
                    road_id=road.road_id,
                    detected_at=datetime.utcnow(),
                    anomaly_score=ml_result.get("anomaly_score"),
                    anomaly_type="SPIKE" if is_anomaly else "NORMAL",
                    normal_vehicle_count=int(previous_traffic),
                    actual_vehicle_count=int(vehicle_count),
                    description=f"Predicted {prediction_text} (confidence: {ml_result.get('confidence_score', 0)}%)",
                    status="ACTIVE" if is_anomaly else "RESOLVED",
                )
                db.add(anomaly_record)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

        return AnomalyPredictionResponse(
            prediction=prediction_text,
            is_anomaly=is_anomaly,
            anomaly_score=ml_result.get("anomaly_score"),
            confidence_score=ml_result.get("confidence_score"),
            road_id=str(road.road_id) if road else request.road_id,
            road_name=road_name,
            features_used=features,
            model_status="trained-isolation-forest",
        )


ml_service = MLService()
