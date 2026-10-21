from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.voice import VoiceRouteExtractRequest, VoiceRouteExtractResponse
from app.services.voice_service import extract_route_from_text, get_nlp_model, resolve_model_path

router = APIRouter(
    prefix="/voice",
    tags=["Voice & Speech NLP"]
)


@router.get(
    "/status",
    summary="Check status of Voice Extraction NER model"
)
def get_voice_status():
    """
    Check if the trained spaCy Location NER model is loaded and ready.
    """
    nlp = get_nlp_model()
    model_path = resolve_model_path()
    return {
        "status": "online",
        "model_loaded": nlp is not None,
        "engine": "spaCy Location NER + Catalog + OpenStreetMap Geocoding",
        "model_path": str(model_path) if model_path else None,
        "labels": ["START_LOCATION", "END_LOCATION"] if nlp else [],
        "resolver_ready": True,
        "osm_geocoder_ready": True,
    }


@router.post(
    "/extract-route",
    response_model=VoiceRouteExtractResponse,
    summary="Extract Start and End locations from spoken text/voice transcript"
)
def extract_route_from_voice(
    req: VoiceRouteExtractRequest,
    db: Session = Depends(get_db)
):
    """
    Accepts speech transcript / natural voice text (e.g. 'Traffic from Uppal to Nagole'
    or 'Take me from Inorbit Mall to DLF Cyber City').
    
    Extracts:
      - start_location (Origin) & end_location (Destination)
      - Exact GPS coordinates via OpenStreetMap / Photon geocoding
      - Canonicalized landmark and road names
    
    This unified API powers:
      - Traffic Prediction
      - Accident Risk Prediction
      - Live Map Navigation
    """
    # Safe check in case unit tests invoke this route function directly without Depends injection
    active_db = db if isinstance(db, Session) else None
    result = extract_route_from_text(req.text, db=active_db, resolve_osm=True)

    msg = result.get("message")
    if not result["success"] and not msg:
        if not result["start_location"] and not result["end_location"]:
            msg = "Could not identify start and end locations. Try phrasing as 'From [Origin] to [Destination]'."
        elif not result["start_location"]:
            msg = f"Found destination '{result['end_location']}', but could not detect start location."
        elif not result["end_location"]:
            msg = f"Found origin '{result['start_location']}', but could not detect destination."

    return VoiceRouteExtractResponse(
        success=result["success"],
        start_location=result["start_location"],
        end_location=result["end_location"],
        extracted_start_words=result.get("extracted_start_words"),
        extracted_end_words=result.get("extracted_end_words"),
        search_query_origin=result.get("search_query_origin"),
        search_query_destination=result.get("search_query_destination"),
        start_latitude=result.get("start_latitude"),
        start_longitude=result.get("start_longitude"),
        end_latitude=result.get("end_latitude"),
        end_longitude=result.get("end_longitude"),
        start_formatted=result.get("start_formatted"),
        end_formatted=result.get("end_formatted"),
        start_status=result.get("start_status"),
        end_status=result.get("end_status"),
        osm_resolved=result.get("osm_resolved", False),
        raw_text=result["raw_text"],
        cleaned_text=result["cleaned_text"],
        method=result["method"],
        model_loaded=result["model_loaded"],
        message=msg
    )
