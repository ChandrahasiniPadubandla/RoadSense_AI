from datetime import datetime, timedelta

from app.schemas.ml import (
    AnomalyPredictionRequest,
    AnomalyPredictionResponse,
    CongestionPredictionRequest,
    CongestionPredictionResponse,
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


ml_service = MLService()
