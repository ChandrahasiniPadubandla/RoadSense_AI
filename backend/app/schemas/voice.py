from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class VoiceRouteExtractRequest(BaseModel):
    text: str = Field(
        ...,
        description="Spoken text or transcribed speech query, e.g. 'Traffic from Uppal to Nagole'"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "What is the traffic from Banjara Hills to Hitec City?"
            }
        }
    }


class VoiceRouteExtractResponse(BaseModel):
    success: bool
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    start_formatted: Optional[str] = None
    end_formatted: Optional[str] = None
    start_status: Optional[str] = None
    end_status: Optional[str] = None
    osm_resolved: bool = False
    raw_text: str
    cleaned_text: Optional[str] = None
    method: str = Field(..., description="'ner', 'pattern', 'catalog', 'hybrid', 'osm', or 'none'")
    model_loaded: bool
    message: Optional[str] = None
