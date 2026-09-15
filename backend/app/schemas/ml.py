from pydantic import BaseModel, Field


class CongestionPredictionRequest(BaseModel):
    road_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    road_type: str = Field(min_length=1)
    hour: int = Field(ge=0, le=23)
    day_of_week: str = Field(min_length=1)
    holiday: int = Field(ge=0, le=1)
    vehicle_count: int = Field(ge=0)
    average_speed: float = Field(ge=0)
    traffic_density: float = Field(ge=0, le=100)
    road_capacity: int = Field(gt=0)
    previous_traffic: int = Field(ge=0)
    weather: str = Field(min_length=1)
    rainfall: float = Field(ge=0)
    temperature: float
    visibility: float = Field(ge=0)
    road_condition: str = Field(min_length=1)
    historical_accidents: int = Field(ge=0)


class CongestionPredictionResponse(BaseModel):
    predicted_congestion: str
    expected_congestion_time: str
    model_status: str = "mock"


class AnomalyPredictionRequest(BaseModel):
    vehicle_count: int = Field(ge=0)
    average_speed: float = Field(ge=0)
    traffic_density: float = Field(ge=0, le=100)
    road_capacity: int = Field(gt=0)
    previous_traffic: int = Field(ge=0)


class AnomalyPredictionResponse(BaseModel):
    prediction: str
    model_status: str = "mock"
