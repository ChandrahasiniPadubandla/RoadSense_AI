from typing import Optional

from pydantic import BaseModel, Field


class CongestionPredictionRequest(BaseModel):
    road_id: str = Field(min_length=1)
    location: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    road_type: Optional[str] = None
    hour: Optional[int] = Field(default=None, ge=0, le=23)
    day_of_week: Optional[str] = None
    holiday: Optional[int] = Field(default=None, ge=0, le=1)
    vehicle_count: Optional[int] = Field(default=None, ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    traffic_density: Optional[float] = Field(default=None, ge=0, le=100)
    road_capacity: Optional[int] = Field(default=None, gt=0)
    previous_traffic: Optional[int] = Field(default=None, ge=0)
    weather: Optional[str] = None
    rainfall: Optional[float] = Field(default=None, ge=0)
    temperature: Optional[float] = None
    visibility: Optional[float] = Field(default=None, ge=0)
    road_condition: Optional[str] = None
    historical_accidents: Optional[int] = Field(default=None, ge=0)


class CongestionPredictionResponse(BaseModel):
    predicted_congestion: str
    expected_congestion_time: str
    model_status: str = "database-backed"


class AnomalyPredictionRequest(BaseModel):
    road_id: Optional[str] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    vehicle_count: Optional[int] = Field(default=None, ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    traffic_density: Optional[float] = Field(default=None, ge=0)
    road_capacity: Optional[int] = Field(default=None, gt=0)
    previous_traffic: Optional[int] = Field(default=None, ge=0)
    hour: Optional[int] = Field(default=None, ge=0, le=23)
    persist: Optional[bool] = False


class AnomalyPredictionResponse(BaseModel):
    prediction: str
    is_anomaly: bool = False
    anomaly_score: Optional[float] = None
    confidence_score: Optional[float] = None
    road_id: Optional[str] = None
    road_name: Optional[str] = None
    features_used: Optional[dict] = None
    model_status: str = "trained-isolation-forest"


class HotspotItem(BaseModel):
    road_id: str
    location: str
    latitude: float
    longitude: float
    accident_count: int
    risk_level: str


class HotspotRequest(BaseModel):
    top_n: int = Field(default=15, ge=1, le=100)


class HotspotResponse(BaseModel):
    hotspots: list[HotspotItem]
    model_status: str = "mock"
