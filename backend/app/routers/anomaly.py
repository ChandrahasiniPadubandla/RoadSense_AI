from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import TrafficAnomaly, Road
from app.schemas.ml import AnomalyPredictionRequest, AnomalyPredictionResponse
from app.services.ml_service import ml_service


router = APIRouter(
    prefix="/anomalies",
    tags=["Traffic Anomaly Detection"],
)


@router.post(
    "/predict",
    response_model=AnomalyPredictionResponse,
    summary="Detect traffic anomalies using trained Isolation Forest ML model",
)
def predict_anomaly(
    request: AnomalyPredictionRequest,
) -> AnomalyPredictionResponse:
    """
    Accepts road_id and/or real-time traffic telemetry features:
      - vehicle_count
      - average_speed
      - traffic_density
      - road_capacity
      - previous_traffic
      - hour
    Executes the trained Isolation Forest model from RoadSense_AI/traffic_congestion.
    """
    return ml_service.predict_anomaly(request)


@router.post(
    "/detect",
    response_model=AnomalyPredictionResponse,
    summary="Detect traffic anomalies (alias for /predict)",
)
def detect_anomaly_alias(
    request: AnomalyPredictionRequest,
) -> AnomalyPredictionResponse:
    return ml_service.predict_anomaly(request)


@router.get(
    "",
    summary="Get recorded traffic anomalies from the database",
)
def list_traffic_anomalies(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns recorded traffic anomalies from the database.
    """
    try:
        records = (
            db.query(TrafficAnomaly)
            .order_by(TrafficAnomaly.detected_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "anomaly_id": str(r.anomaly_id),
                "road_id": str(r.road_id),
                "road_name": r.road.road_name if r.road else None,
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                "anomaly_score": float(r.anomaly_score) if r.anomaly_score is not None else None,
                "anomaly_type": r.anomaly_type,
                "normal_vehicle_count": r.normal_vehicle_count,
                "actual_vehicle_count": r.actual_vehicle_count,
                "description": r.description,
                "status": r.status,
            }
            for r in records
        ]
    except Exception as e:
        return []
