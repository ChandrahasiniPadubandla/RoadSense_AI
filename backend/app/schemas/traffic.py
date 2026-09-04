from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ZoneCreate(BaseModel):
    zone_name: str
    description: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ZoneResponse(BaseModel):
    zone_id: int
    zone_name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# ROAD
# ============================================

class RoadCreate(BaseModel):

    zone_id: Optional[int] = None

    road_name: str

    road_type: Optional[str] = None

    start_latitude: Optional[float] = None

    start_longitude: Optional[float] = None

    end_latitude: Optional[float] = None

    end_longitude: Optional[float] = None

    road_capacity: Optional[int] = None

    speed_limit: Optional[float] = None

    road_condition: Optional[str] = None

    number_of_lanes: Optional[int] = None


class RoadResponse(BaseModel):

    road_id: int

    zone_id: Optional[int]

    road_name: str

    road_type: Optional[str]

    road_capacity: Optional[int]

    speed_limit: Optional[float]

    road_condition: Optional[str]

    number_of_lanes: Optional[int]

    is_active: bool

    class Config:
        from_attributes = True


# ============================================
# TRAFFIC RECORD
# ============================================

class TrafficCreate(BaseModel):

    road_id: int

    timestamp: datetime

    vehicle_count: int = Field(ge=0)

    average_speed: Optional[float] = Field(
        default=None,
        ge=0
    )

    traffic_density: Optional[float] = Field(
        default=None,
        ge=0,
        le=100
    )

    congestion_level: Optional[str] = None

    road_condition: Optional[str] = None

    weather_condition: Optional[str] = None

    rainfall: Optional[float] = Field(
        default=None,
        ge=0
    )

    temperature: Optional[float] = None

    visibility: Optional[float] = Field(
        default=None,
        ge=0
    )

    is_holiday: bool = False


class TrafficResponse(BaseModel):

    traffic_id: int

    road_id: int

    timestamp: datetime

    vehicle_count: int

    average_speed: Optional[float]

    traffic_density: Optional[float]

    congestion_level: Optional[str]

    road_condition: Optional[str]

    weather_condition: Optional[str]

    rainfall: Optional[float]

    temperature: Optional[float]

    visibility: Optional[float]

    is_holiday: bool

    class Config:
        from_attributes = True