from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AccidentRiskPredictionRequest(BaseModel):
    road_id: Optional[UUID] = Field(default=None, description="Database road_id to derive real ML features from")
    road_name: Optional[str] = Field(default=None, description="Searched road name to resolve via geocoding and create if not in DB")

    @model_validator(mode="after")
    def check_road_identifier(self):
        if self.road_id is None and not (self.road_name and self.road_name.strip()):
            raise ValueError("Either road_id or road_name must be provided.")
        return self


class RoadSearchResult(BaseModel):
    road_id: UUID
    road_name: str


class AccidentRiskPredictionResponse(BaseModel):
    success: bool = True
    road_id: UUID
    road_name: str
    accident_risk: float = Field(..., ge=0.0, le=100.0)
    accident_risk_level: str = Field(..., min_length=1)
    created_new_road: bool = False
    model_status: str = "loaded"

    class Config:
        from_attributes = True

