from fastapi import APIRouter

from app.schemas.ml import (
    AnomalyPredictionRequest,
    AnomalyPredictionResponse,
    CongestionPredictionRequest,
    CongestionPredictionResponse,
)
from app.services.ml_service import ml_service


router = APIRouter(
    tags=["ML Predictions"],
)


@router.post(
    "/predict-congestion",
    response_model=CongestionPredictionResponse,
    summary="Predict traffic congestion",
)
def predict_congestion(
    request: CongestionPredictionRequest,
) -> CongestionPredictionResponse:
    return ml_service.predict_congestion(request)


@router.post(
    "/predict-anomaly",
    response_model=AnomalyPredictionResponse,
    summary="Detect traffic anomalies (compatibility route)",
)
def predict_anomaly_compatibility(
    request: AnomalyPredictionRequest,
) -> AnomalyPredictionResponse:
    return ml_service.predict_anomaly(request)
