from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import Road, TrafficZone
from app.schemas.voice import VoiceRouteExtractRequest, VoiceRouteExtractResponse
from app.services.voice_service import extract_route_from_text

router = APIRouter(
    prefix="/voice",
    tags=["Voice & Speech NLP"]
)


@router.get(
    "/status",
    summary="Check status of the database-backed location resolver"
)
def get_voice_status(db: Session = Depends(get_db)):
    """
    Check connectivity for the database-backed location resolver.
    """
    db.query(Road.road_id).limit(1).all()
    db.query(TrafficZone.zone_id).limit(1).all()
    return {
        "status": "online",
        "resolver_ready": True,
        "model_loaded": False,
        "engine": "Geocoding API location resolver (Photon/OpenStreetMap)",
        "labels": []
    }


@router.post(
    "/extract-route",
    response_model=VoiceRouteExtractResponse,
    summary="Extract Start and End locations from spoken text/voice transcript"
)
def extract_route_from_voice(
    req: VoiceRouteExtractRequest,
    db: Session = Depends(get_db),
):
    """
    Accepts a speech transcript, parses the origin/destination phrases, and
    resolves each *complete* phrase to a real place through the backend geocoding
    provider. The full recognized place name is returned (never shortened);
    ambiguous, missing, timed-out or rate-limited lookups are surfaced as clear
    validation results instead of being silently substituted.

    This unified API powers:
      - Traffic Prediction
      - Accident Risk Prediction
      - Live Map Navigation
    """
    result = extract_route_from_text(req.text, db)
    start_coordinates = result.get("start_coordinates") or {}
    end_coordinates = result.get("end_coordinates") or {}
    return VoiceRouteExtractResponse(
        success=result["success"],
        start_location=result["start_location"],
        end_location=result["end_location"],
        start_status=result["start_status"],
        end_status=result["end_status"],
        start_matches=result["start_matches"],
        end_matches=result["end_matches"],
        start_latitude=start_coordinates.get("latitude"),
        start_longitude=start_coordinates.get("longitude"),
        end_latitude=end_coordinates.get("latitude"),
        end_longitude=end_coordinates.get("longitude"),
        raw_text=result["raw_text"],
        cleaned_text=result["cleaned_text"],
        method=result["method"],
        resolver_ready=result["resolver_ready"],
        model_loaded=result["model_loaded"],
        message=result["message"]
    )
