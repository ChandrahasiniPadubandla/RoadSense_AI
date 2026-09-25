from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import Road, TrafficRecord
from app.schemas.ml import (
    AnomalyPredictionRequest,
    AnomalyPredictionResponse,
)


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
                .order_by(TrafficRecord.timestamp.desc())
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
        from app.ml.prediction_engine import trigger_ml_anomaly_model

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
            from app.ml.prediction_engine import resolve_route_bundle
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

        vehicle_count = request.vehicle_count
        if vehicle_count is None:
            vehicle_count = int(traffic.vehicle_count) if (traffic and traffic.vehicle_count is not None) else 800

        average_speed = request.average_speed
        if average_speed is None:
            average_speed = float(traffic.average_speed) if (traffic and traffic.average_speed is not None) else 35.0

        traffic_density = request.traffic_density
        if traffic_density is None:
            traffic_density = float(traffic.traffic_density) if (traffic and traffic.traffic_density is not None) else 45.0

        road_capacity = request.road_capacity
        if road_capacity is None:
            road_capacity = int(road.road_capacity) if (road and road.road_capacity is not None) else 1500

        previous_traffic = request.previous_traffic
        if previous_traffic is None:
            previous_traffic = int(traffic.vehicle_count * 0.95) if (traffic and traffic.vehicle_count is not None) else 750

        hour = request.hour
        if hour is None:
            from datetime import datetime
            hour = traffic.timestamp.hour if (traffic and traffic.timestamp) else datetime.now().hour

        features = {
            "vehicle_count": vehicle_count,
            "average_speed": average_speed,
            "traffic_density": traffic_density,
            "road_capacity": road_capacity,
            "previous_traffic": previous_traffic,
            "hour": hour,
        }

        ml_result = trigger_ml_anomaly_model(features)
        prediction_text = ml_result["prediction"]
        is_anomaly = ml_result["is_anomaly"]

        if request.persist and road:
            from datetime import datetime, timezone
            from app.database.models import TrafficAnomaly
            db = SessionLocal()
            try:
                anomaly_record = TrafficAnomaly(
                    road_id=road.road_id,
                    timestamp=datetime.now(timezone.utc),
                    is_anomaly=is_anomaly,
                    anomaly_score=ml_result.get("anomaly_score"),
                    vehicle_count=vehicle_count,
                    average_speed=average_speed,
                    traffic_density=traffic_density,
                    confidence_score=ml_result.get("confidence_score"),
                    status="RESOLVED" if not is_anomaly else "DETECTED",
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