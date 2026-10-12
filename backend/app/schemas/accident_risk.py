from uuid import UUID

from pydantic import BaseModel, Field


class AccidentRiskPredictionRequest(BaseModel):
    road_id: UUID = Field(..., description="Database road_id to derive real ML features from")


class RoadSearchResult(BaseModel):
    road_id: UUID
    road_name: str


class AccidentRiskPredictionResponse(BaseModel):
    success: bool = True
    road_id: UUID
    road_name: str
    accident_risk: float = Field(..., ge=0.0, le=100.0)
    accident_risk_level: str = Field(..., min_length=1)
    model_status: str = "loaded"

    class Config:
        from_attributes = True
