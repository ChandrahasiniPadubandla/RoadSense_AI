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
    / "ML"
    / "dataset"
    / "traffic_accident_balanced_10000.csv"
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
        road = self._get_road_record(request.road_id)
        traffic = self._get_latest_traffic(str(road.road_id))

        vehicle_count = int(request.vehicle_count) if request.vehicle_count is not None else int(traffic.vehicle_count or 0)
        previous_traffic = int(request.previous_traffic) if request.previous_traffic is not None else int(traffic.vehicle_count or 0)
        road_capacity = int(request.road_capacity) if request.road_capacity is not None else int(road.road_capacity or 1)
        density = float(request.traffic_density) if request.traffic_density is not None else float(traffic.traffic_density or 0)

        capacity_ratio = vehicle_count / max(road_capacity, 1)
        traffic_change = abs(vehicle_count - previous_traffic) / max(previous_traffic, 1)
        is_anomaly = (
            density >= 90
            or capacity_ratio >= 1.0
            or traffic_change >= 0.5
        )

        return AnomalyPredictionResponse(
            prediction="ANOMALY" if is_anomaly else "NORMAL",
            model_status="database-backed",
        )

    def get_accident_hotspots(
        self,
        request: HotspotRequest,
    ) -> HotspotResponse:
        import pandas as pd

        df = pd.read_csv(DATASET_PATH)

        accident_data = df[df["accident_occurred"] == 1].copy()

        hotspots = (
            accident_data
            .groupby(["location", "latitude", "longitude"])
            .size()
            .reset_index(name="accident_count")
            .sort_values("accident_count", ascending=False)
            .head(request.top_n)
            .reset_index(drop=True)
        )

        road_for_location = (
            accident_data
            .groupby("location")["road_id"]
            .agg(lambda ids: ids.mode().iloc[0])
            .to_dict()
        )
        hotspots["road_id"] = hotspots["location"].map(road_for_location)

        def _risk_level(count: int) -> str:
            if count >= 700:
                return "HIGH"
            elif count >= 600:
                return "MEDIUM"
            return "LOW"

        hotspots["risk_level"] = hotspots["accident_count"].apply(_risk_level)

        items = [
            HotspotItem(
                road_id=row["road_id"],
                location=row["location"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                accident_count=int(row["accident_count"]),
                risk_level=row["risk_level"],
            )
            for _, row in hotspots.iterrows()
        ]

        return HotspotResponse(hotspots=items, model_status="dataset-backed")


ml_service = MLService()