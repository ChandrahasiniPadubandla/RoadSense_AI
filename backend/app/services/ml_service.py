from datetime import datetime, timedelta
from pathlib import Path

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
    """Stable ML integration boundary with deterministic placeholders for now."""

    def predict_congestion(
        self,
        request: CongestionPredictionRequest,
    ) -> CongestionPredictionResponse:
        # TODO: Replace with real Random Forest inference when ML model is available.
        density = request.traffic_density
        if density < 30:
            level = "LOW"
        elif density < 60:
            level = "MEDIUM"
        elif density < 80:
            level = "HIGH"
        else:
            level = "SEVERE"

        start = datetime.now().replace(
            hour=request.hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        end = start + timedelta(hours=1)
        expected_time = f"{start.strftime('%I:%M %p').lstrip('0')} - {end.strftime('%I:%M %p').lstrip('0')}"

        return CongestionPredictionResponse(
            predicted_congestion=level,
            expected_congestion_time=expected_time,
        )

    def predict_anomaly(
        self,
        request: AnomalyPredictionRequest,
    ) -> AnomalyPredictionResponse:
        # TODO: Replace with Isolation Forest inference when ML model is available.
        capacity_ratio = request.vehicle_count / request.road_capacity
        traffic_change = (
            abs(request.vehicle_count - request.previous_traffic)
            / max(request.previous_traffic, 1)
        )
        is_anomaly = (
            request.traffic_density >= 90
            or capacity_ratio >= 1.0
            or traffic_change >= 0.5
        )

        return AnomalyPredictionResponse(
            prediction="ANOMALY" if is_anomaly else "NORMAL",
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

        return HotspotResponse(hotspots=items)


ml_service = MLService()
