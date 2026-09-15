from fastapi import APIRouter

from app.schemas.ml import HotspotRequest, HotspotResponse
from app.services.ml_service import ml_service


router = APIRouter(
    tags=["Accident Hotspot Analysis"],
)


@router.post(
    "/predict",
    response_model=HotspotResponse,
    summary="Identify top accident hotspots",
)
def get_accident_hotspots(
    request: HotspotRequest,
) -> HotspotResponse:
    return ml_service.get_accident_hotspots(request)
