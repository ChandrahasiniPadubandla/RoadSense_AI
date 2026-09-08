from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# =========================================================
# TRAFFIC PREDICTION SCHEMAS
# =========================================================

class TrafficPredictionCreate(BaseModel):
    road_id: UUID
    target_time: datetime
    predicted_congestion: str = Field(..., description="LOW, MEDIUM, HIGH, SEVERE")
    predicted_vehicle_count: Optional[int] = Field(default=None, ge=0)
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    model_version_id: Optional[UUID] = None


class TrafficPredictionResponse(BaseModel):
    prediction_id: UUID
    road_id: UUID
    road_name: Optional[str] = None
    prediction_time: datetime
    target_time: datetime
    predicted_congestion: str
    predicted_vehicle_count: Optional[int] = None
    confidence_score: Optional[float] = None
    model_version_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrafficEstimateRequest(BaseModel):
    road_id: UUID
    target_minutes_ahead: Optional[int] = Field(default=30, ge=5, le=1440)
    vehicle_count: Optional[int] = Field(default=None, ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    rainfall: Optional[float] = Field(default=0.0, ge=0)
    temperature: Optional[float] = None
    is_holiday: Optional[bool] = False


# =========================================================
# ACCIDENT PREDICTION SCHEMAS
# =========================================================

class AccidentPredictionCreate(BaseModel):
    road_id: UUID
    risk_percentage: float = Field(..., ge=0.0, le=100.0, description="Estimated risk percentage 0.0 - 100.0")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    model_version_id: Optional[UUID] = None


class AccidentPredictionResponse(BaseModel):
    prediction_id: UUID
    road_id: UUID
    road_name: Optional[str] = None
    prediction_time: datetime
    risk_percentage: float
    risk_level: str
    confidence_score: Optional[float] = None
    model_version_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccidentEstimateRequest(BaseModel):
    road_id: UUID
    traffic_density: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    weather_condition: Optional[str] = None
    rainfall: Optional[float] = Field(default=0.0, ge=0)
    visibility: Optional[float] = None
    road_condition: Optional[str] = None


class RoadRiskSummary(BaseModel):
    road_id: UUID
    road_name: str
    latest_predicted_congestion: Optional[str] = None
    latest_accident_risk_level: Optional[str] = None
    risk_percentage: Optional[float] = None
    color: str
    last_updated: Optional[datetime] = None


class PredictionPipelineRunResponse(BaseModel):
    status: str
    message: str
    scanned_roads: int
    traffic_predictions_generated: int
    accident_predictions_generated: int
    alerts_raised: int
    timestamp: datetime

