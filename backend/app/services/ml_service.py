from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import Road, TrafficRecord
from app.schemas.ml import (
    AnomalyPredictionRequest,
    AnomalyPredictionResponse,
    CongestionPredictionRequest,
    CongestionPredictionResponse,
    HotspotRequest,
    HotspotResponse,
    HotspotItem,
)

DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "predict_accident_risk"
    / "dataset"
    / "hyderabad_traffic_accident_balanced_15000.csv"
)


class MLService:
    """Database-backed ML compatibility service."""

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

    def predict_congestion(
        self,
        request: CongestionPredictionRequest,
    ) -> CongestionPredictionResponse:
        road = self._get_road_record(request.road_id)
        traffic = self._get_latest_traffic(str(road.road_id))

        density = float(request.traffic_density) if request.traffic_density is not None else float(traffic.traffic_density or 0)
        if density < 30:
            level = "LOW"
        elif density < 60:
            level = "MEDIUM"
        elif density < 80:
            level = "HIGH"
        else:
            level = "SEVERE"

        hour = int(request.hour) if request.hour is not None else (traffic.timestamp.hour if traffic.timestamp else datetime.now().hour)
        start = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        expected_time = f"{start.strftime('%I:%M %p').lstrip('0')} - {end.strftime('%I:%M %p').lstrip('0')}"

        return CongestionPredictionResponse(
            predicted_congestion=level,
            expected_congestion_time=expected_time,
            model_status="database-backed",
        )

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

        road_capacity = request.road_capacity
        if road_capacity is None:
            road_capacity = int(road.road_capacity) if (road and road.road_capacity) else 1200

        traffic_density = request.traffic_density
        if traffic_density is None:
            if traffic and traffic.traffic_density is not None:
                traffic_density = float(traffic.traffic_density)
            elif road_capacity > 0:
                traffic_density = round((vehicle_count / road_capacity) * 100.0, 2)
            else:
                traffic_density = 50.0

        previous_traffic = request.previous_traffic
        if previous_traffic is None:
            previous_traffic = int(traffic.vehicle_count) if (traffic and traffic.vehicle_count is not None) else int(vehicle_count * 0.95)

        hour = request.hour
        if hour is None:
            if traffic and traffic.timestamp:
                hour = traffic.timestamp.hour
            else:
                hour = datetime.now().hour

        features = {
            "vehicle_count": float(vehicle_count),
            "average_speed": float(average_speed),
            "traffic_density": float(traffic_density),
            "road_capacity": float(road_capacity),
            "previous_traffic": float(previous_traffic),
            "hour": float(hour)
        }

        ml_result = trigger_ml_anomaly_model(features)
        is_anomaly = ml_result.get("is_anomaly", ml_result.get("prediction") == "ANOMALY")
        prediction_text = ml_result.get("prediction", "ANOMALY" if is_anomaly else "NORMAL")

        if request.persist and road:
            db = SessionLocal()
            try:
                from app.database.models import TrafficAnomaly
                anomaly_entry = TrafficAnomaly(
                    road_id=road.road_id,
                    traffic_id=traffic.traffic_id if traffic else None,
                    detected_at=datetime.utcnow(),
                    normal_vehicle_count=int(previous_traffic),
                    actual_vehicle_count=int(vehicle_count),
                    anomaly_score=ml_result.get("anomaly_score"),
                    anomaly_type="SURGE_CONGESTION" if vehicle_count > road_capacity else "IRREGULAR_FLOW",
                    description=f"Isolation Forest detected traffic anomaly with score {ml_result.get('anomaly_score')}.",
                    status="ACTIVE"
                )
                db.add(anomaly_entry)
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

    def get_accident_hotspots(
        self,
        request: HotspotRequest,
    ) -> HotspotResponse:
        import pandas as pd

        df = pd.read_csv(DATASET_PATH)

        accident_data = df[df["accident_occurred"] == 1].copy()

        loc_col = "location" if "location" in accident_data.columns else "start_location"
        lat_col = "latitude" if "latitude" in accident_data.columns else "start_latitude"
        lng_col = "longitude" if "longitude" in accident_data.columns else "start_longitude"

        hotspots = (
            accident_data
            .groupby([loc_col, lat_col, lng_col])
            .size()
            .reset_index(name="accident_count")
            .sort_values("accident_count", ascending=False)
            .head(request.top_n)
            .reset_index(drop=True)
        )

        road_for_location = (
            accident_data
            .groupby(loc_col)["road_id"]
            .agg(lambda ids: ids.mode().iloc[0])
            .to_dict()
        )
        hotspots["road_id"] = hotspots[loc_col].map(road_for_location)

        def _risk_level(count: int) -> str:
            if count >= 100:
                return "HIGH"
            elif count >= 50:
                return "MEDIUM"
            return "LOW"

        hotspots["risk_level"] = hotspots["accident_count"].apply(_risk_level)

        items = [
            HotspotItem(
                road_id=row["road_id"],
                location=row[loc_col],
                latitude=row[lat_col],
                longitude=row[lng_col],
                accident_count=int(row["accident_count"]),
                risk_level=row["risk_level"],
            )
            for _, row in hotspots.iterrows()
        ]

        return HotspotResponse(hotspots=items, model_status="dataset-backed")


ml_service = MLService()