from typing import Optional
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
    raw_text: str
    cleaned_text: Optional[str] = None
    method: str = Field(..., description="'ner', 'pattern', 'hybrid', or 'none'")
    model_loaded: bool
    message: Optional[str] = None
