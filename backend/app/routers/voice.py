from fastapi import APIRouter, HTTPException, Depends
from app.schemas.voice import VoiceRouteExtractRequest, VoiceRouteExtractResponse
from app.services.voice_service import extract_route_from_text, get_nlp_model

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
    return {
        "status": "online",
        "model_loaded": nlp is not None,
        "engine": "spaCy Location NER + Hybrid Regex Fallback",
        "labels": ["START_LOCATION", "END_LOCATION"] if nlp else []
    }


@router.post(
    "/extract-route",
    response_model=VoiceRouteExtractResponse,
    summary="Extract Start and End locations from spoken text/voice transcript"
)
def extract_route_from_voice(req: VoiceRouteExtractRequest):
    """
    Accepts speech transcript / natural voice text (e.g. 'Traffic from Uppal to Nagole'
    or 'What is the accident risk between Banjara Hills and Hitec City?').
    
    Extracts:
      - start_location (Origin)
      - end_location (Destination)
    
    This unified API powers:
      - Traffic Prediction
      - Accident Risk Prediction
      - Live Map Navigation
    """
    result = extract_route_from_text(req.text)

    msg = None
    if not result["success"]:
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
        raw_text=result["raw_text"],
        cleaned_text=result["cleaned_text"],
        method=result["method"],
        model_loaded=result["model_loaded"],
        message=msg
    )
