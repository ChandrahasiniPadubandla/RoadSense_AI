from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class VoiceLocationMatch(BaseModel):
    name: str
    source: str
    score: float = Field(ge=0, le=1)


class VoiceRouteExtractRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Spoken text or transcribed speech query, e.g. 'Traffic from Uppal to Nagole'"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "What is the traffic from Banjara Hills to Hitec City?"
            }
        }
    }


VoiceLocationStatus = Literal[
    "empty",
    "matched",
    "ambiguous",
    "not_found",
    "timeout",
    "rate_limited",
    "error",
]


class VoiceRouteExtractResponse(BaseModel):
    success: bool
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    start_status: VoiceLocationStatus
    end_status: VoiceLocationStatus
    start_matches: List[VoiceLocationMatch] = Field(default_factory=list)
    end_matches: List[VoiceLocationMatch] = Field(default_factory=list)
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    raw_text: str
    cleaned_text: Optional[str] = None
    method: str = Field(..., description="'geocoding', 'partial', or 'none'")
    resolver_ready: bool
    model_loaded: bool = False
    message: Optional[str] = None
