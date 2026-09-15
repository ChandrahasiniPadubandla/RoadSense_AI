from fastapi import APIRouter

from app.schemas.ml import AnomalyPredictionRequest, AnomalyPredictionResponse
from app.services.ml_service import ml_service


router = APIRouter(
    tags=["Traffic Anomaly Detection"],
)


@router.post(
    "/predict",
    response_model=AnomalyPredictionResponse,
    summary="Detect traffic anomalies",
)
def predict_anomaly(
    request: AnomalyPredictionRequest,
) -> AnomalyPredictionResponse:
    return ml_service.predict_anomaly(request)
