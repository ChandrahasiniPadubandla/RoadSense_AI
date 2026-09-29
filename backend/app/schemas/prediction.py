from uuid import UUID
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


# =========================================================
# 1. AI TRAFFIC PREDICTION SCHEMAS
# =========================================================

class TrafficPredictionRunRequest(BaseModel):
    """
    Request model to run traffic congestion prediction on-demand.
    ML teams can pass pre-computed predictions or raw road telemetry.
    """
    road_id: UUID
    target_time: Optional[datetime] = Field(
        default=None,
        description="Target prediction datetime (defaults to 30 mins from now)"
    )
    target_minutes_ahead: Optional[int] = Field(
        default=30,
        ge=5,
        le=1440,
        description="Minutes ahead to predict if target_time is not set"
    )

    # ML Output overrides (if ML people are pushing their calculated prediction)
    predicted_congestion: Optional[str] = Field(
        default=None,
        description="Optional pre-computed congestion: LOW, MEDIUM, HIGH, SEVERE"
    )
    predicted_vehicle_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional pre-computed vehicle count"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional model confidence score (0-100)"
    )

    # Telemetry inputs for model inference
    vehicle_count: Optional[int] = Field(default=None, ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0.0)
    traffic_density: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    weather: Optional[str] = Field(default=None, description="Clear, Rainy, Foggy, Overcast")
    rainfall: Optional[float] = Field(default=0.0, ge=0.0)
    temperature: Optional[float] = None
    road_condition: Optional[str] = Field(default=None, description="Good, Fair, Poor, Wet")
    is_holiday: Optional[bool] = False
    persist: bool = Field(
        default=True,
        description="Whether to save the prediction into database traffic_predictions"
    )


class TrafficPredictionRunResponse(BaseModel):
    """
    Output model for Traffic Congestion Prediction.
    Specifically provides congestion_level and estimated_time window (e.g. '4:00 PM - 5:00 PM').
    """
    prediction_id: Optional[UUID] = None
    road_id: UUID
    road_name: Optional[str] = None
    congestion_level: str = Field(..., description="Congestion level: LOW, MEDIUM, HIGH, SEVERE")
    estimated_time: str = Field(..., description="Estimated time window, e.g. '4:00 PM - 5:00 PM (4pm to 5pm)'")
    target_time: datetime
    predicted_congestion: str = Field(..., description="Alias for congestion_level for compatibility")
    predicted_vehicle_count: Optional[int] = None
    confidence_score: Optional[float] = None
    class_probabilities: Optional[Dict[str, float]] = None
    anomaly_detection: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class TrafficPredictionCreate(BaseModel):
    """Direct database ingestion schema for ML team data pipelines."""
    road_id: UUID
    target_time: datetime
    predicted_congestion: str = Field(..., description="LOW, MEDIUM, HIGH, SEVERE")
    predicted_vehicle_count: Optional[int] = Field(default=None, ge=0)
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    model_version_id: Optional[UUID] = None


class TrafficPredictionResponse(BaseModel):
    """Standard traffic prediction response stored in database."""
    prediction_id: UUID
    road_id: UUID
    road_name: Optional[str] = None
    prediction_time: datetime
    target_time: datetime
    congestion_level: str
    estimated_time: str
    predicted_congestion: str
    predicted_vehicle_count: Optional[int] = None
    confidence_score: Optional[float] = None
    model_version_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrafficEstimateRequest(BaseModel):
    """Legacy request schema retained for backward compatibility."""
    road_id: UUID
    target_minutes_ahead: Optional[int] = Field(default=30, ge=5, le=1440)
    vehicle_count: Optional[int] = Field(default=None, ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    rainfall: Optional[float] = Field(default=0.0, ge=0)
    temperature: Optional[float] = None
    is_holiday: Optional[bool] = False


# =========================================================
# 2. AI ACCIDENT PREDICTION SCHEMAS
# =========================================================

class AccidentPredictionRunRequest(BaseModel):
    """
    Request model to run accident risk prediction on-demand.
    ML teams can pass pre-computed risk metrics or telemetry features.
    """
    road_id: Optional[UUID] = None
    road_name: Optional[str] = Field(
        default=None,
        description="Searched road name to resolve via geocoding and create if not in DB"
    )

    # Direct ML Output overrides
    risk_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional pre-computed risk percentage (0.0 to 100.0)"
    )
    risk_level: Optional[str] = Field(
        default=None,
        description="Optional pre-computed risk level: LOW, MEDIUM, HIGH, CRITICAL"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional model confidence score (0-100)"
    )

    # Telemetry inputs for model inference
    traffic_density: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    average_speed: Optional[float] = Field(default=None, ge=0.0)
    weather_condition: Optional[str] = Field(default=None)
    rainfall: Optional[float] = Field(default=0.0, ge=0.0)
    visibility: Optional[float] = Field(default=None, ge=0.0)
    road_condition: Optional[str] = Field(default=None)
    historical_accidents: Optional[int] = Field(default=None, ge=0)
    persist: bool = Field(
        default=True,
        description="Whether to save the prediction into database accident_predictions"
    )


class AccidentPredictionRunResponse(BaseModel):
    """
    Output model for Accident Prediction.
    Specifically provides risk_percentage and categorical risk_level.
    """
    prediction_id: Optional[UUID] = None
    road_id: UUID
    road_name: Optional[str] = None
    risk_percentage: float = Field(..., description="Estimated accident risk percentage (0.0 - 100.0%)")
    risk_level: str = Field(..., description="Categorical risk level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence_score: Optional[float] = None
    created_new_road: bool = Field(default=False, description="True if this road was newly geocoded and created in the database")
    prediction_time: datetime
    created_at: Optional[datetime] = None


class AccidentPredictionCreate(BaseModel):
    """Direct database ingestion schema for ML team data pipelines."""
    road_id: UUID
    risk_percentage: float = Field(..., ge=0.0, le=100.0, description="Estimated risk percentage 0.0 - 100.0")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    model_version_id: Optional[UUID] = None


class AccidentPredictionResponse(BaseModel):
    """Standard accident prediction response stored in database."""
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
    """Legacy schema retained for backward compatibility."""
    road_id: UUID
    traffic_density: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    weather_condition: Optional[str] = None
    rainfall: Optional[float] = Field(default=0.0, ge=0)
    visibility: Optional[float] = None
    road_condition: Optional[str] = None


# =========================================================
# 3. INTEGRATED SUMMARY & BATCH PIPELINE SCHEMAS
# =========================================================

class RoadRiskSummary(BaseModel):
    road_id: UUID
    road_name: str
    latest_predicted_congestion: Optional[str] = None
    latest_accident_risk_level: Optional[str] = None
    risk_percentage: Optional[float] = None
    color: str
    last_updated: Optional[datetime] = None


class TrafficPipelineRunResponse(BaseModel):
    status: str
    scanned_roads: int
    predictions_generated: int
    severe_alerts_raised: int
    timestamp: datetime


class AccidentPipelineRunResponse(BaseModel):
    status: str
    scanned_roads: int
    predictions_generated: int
    critical_alerts_raised: int
    timestamp: datetime


class PredictionPipelineRunResponse(BaseModel):
    status: str
    message: str
    scanned_roads: int
    traffic_predictions_generated: int
    accident_predictions_generated: int
    alerts_raised: int
    timestamp: datetime


# =========================================================
# 4. ROUTE-BASED PREDICTION SCHEMAS (START & END LOCATIONS)
# =========================================================

class RoutePredictionRequest(BaseModel):
    """
    Request model when user provides start and end locations from frontend.
    Accepts coordinates and/or location names.
    """
    start_location: Optional[str] = Field(default=None, description="Start location name, e.g. 'Banjara Hills'")
    end_location: Optional[str] = Field(default=None, description="End location name, e.g. 'Hitec City'")
    start_latitude: Optional[float] = Field(default=None, description="Start latitude, e.g. 17.4156")
    start_longitude: Optional[float] = Field(default=None, description="Start longitude, e.g. 78.4347")
    end_latitude: Optional[float] = Field(default=None, description="End latitude, e.g. 17.4435")
    end_longitude: Optional[float] = Field(default=None, description="End longitude, e.g. 78.3772")
    road_id: Optional[UUID] = Field(default=None, description="Optional road_id if user selected a known road")
    target_time: Optional[datetime] = Field(default=None, description="Target prediction time")
    target_minutes_ahead: Optional[int] = Field(default=30, ge=5, le=1440)
    persist: bool = Field(default=True, description="Whether to record the generated prediction in the database")

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_location": "Banjara Hills",
                "end_location": "Hitec City"
            }
        }
    }


class RouteTrafficPredictionResponse(BaseModel):
    """
    Traffic Congestion Prediction for user selected route.
    Outputs congestion_level and estimated_time window (e.g. '4:00 PM - 5:00 PM').
    """
    prediction_id: Optional[UUID] = None
    road_id: Optional[UUID] = None
    road_name: str
    start_location: str
    end_location: str
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    distance_km: float
    congestion_level: str = Field(..., description="Predicted congestion level: LOW, MEDIUM, HIGH, SEVERE")
    estimated_time: str = Field(..., description="Estimated time window, e.g. '4:00 PM - 5:00 PM (4pm to 5pm)'")
    target_time: datetime
    confidence_score: Optional[float] = None
    weather_conditions: Dict[str, Any] = Field(default_factory=dict)
    road_conditions: Dict[str, Any] = Field(default_factory=dict)
    previous_records: Dict[str, Any] = Field(default_factory=dict)
    ml_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete feature bundle prepared by the API and passed to the ML model"
    )
    route_geometry: Optional[List[List[float]]] = Field(
        default=None,
        description="Detailed street-level road waypoints [[lat, lng], ...] for interactive map routing"
    )
    accident_points: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Accident incident points and predicted risk hazard points along the route"
    )
    anomaly_detection: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Traffic anomaly detection analysis: prediction (NORMAL/ANOMALY), is_anomaly, anomaly_score, confidence_score"
    )
    live_traffic: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Real-time live traffic telemetry: current speed, free-flow speed, delay, congestion percentage"
    )
    created_new_road: bool = Field(default=False, description="True if this road was newly geocoded and created in the database")
    newly_created_roads: List[str] = Field(default_factory=list, description="Names of roads newly geocoded and saved to the database")
    ml_source: str = Field(default="backend-feature-engine")
    created_at: Optional[datetime] = None


class RouteAccidentPredictionResponse(BaseModel):
    """
    Accident Risk Prediction for user selected route.
    Outputs risk_percentage and categorical risk_level.
    """
    prediction_id: Optional[UUID] = None
    road_id: Optional[UUID] = None
    road_name: str
    start_location: str
    end_location: str
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    distance_km: float
    risk_percentage: float = Field(..., description="Predicted accident risk percentage (0.0 - 100.0%)")
    risk_level: str = Field(..., description="Categorical risk level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence_score: Optional[float] = None
    prediction_time: datetime
    weather_conditions: Dict[str, Any] = Field(default_factory=dict)
    road_conditions: Dict[str, Any] = Field(default_factory=dict)
    previous_records: Dict[str, Any] = Field(default_factory=dict)
    historical_accidents_count: int = 0
    route_geometry: Optional[List[List[float]]] = Field(
        default=None,
        description="Detailed street-level road waypoints [[lat, lng], ...] for interactive map routing"
    )
    accident_points: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Accident incident points and predicted risk hazard points along the route"
    )
    ml_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete feature bundle prepared by the API and passed to the ML model"
    )
    created_new_road: bool = Field(default=False, description="True if this road was newly geocoded and created in the database")
    newly_created_roads: List[str] = Field(default_factory=list, description="Names of roads newly geocoded and saved to the database")
    ml_source: str = Field(default="backend-feature-engine")
    created_at: Optional[datetime] = None


