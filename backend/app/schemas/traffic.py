from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ============================================
# TRAFFIC ZONE
# ============================================

class ZoneCreate(BaseModel):
    zone_name: str
    description: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone_id: UUID
    zone_name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None


# ============================================
# ROAD
# ============================================

class RoadCreate(BaseModel):
    zone_id: Optional[UUID] = None
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
    is_active: Optional[bool] = True


class RoadUpdate(BaseModel):
    zone_id: Optional[UUID] = None
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    road_capacity: Optional[int] = None
    speed_limit: Optional[float] = None
    road_condition: Optional[str] = None
    number_of_lanes: Optional[int] = None
    is_active: Optional[bool] = None


class RoadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    road_id: UUID
    zone_id: Optional[UUID] = None
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
    is_active: bool
    created_at: Optional[datetime] = None


# ============================================
# TRAFFIC RECORD
# ============================================

class TrafficCreate(BaseModel):
    road_id: UUID
    timestamp: datetime
    vehicle_count: int = Field(ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    traffic_density: Optional[float] = Field(default=None, ge=0, le=100)
    congestion_level: Optional[str] = None
    road_condition: Optional[str] = None
    weather_condition: Optional[str] = None
    rainfall: Optional[float] = Field(default=None, ge=0)
    temperature: Optional[float] = None
    visibility: Optional[float] = Field(default=None, ge=0)
    is_holiday: bool = False


class TrafficUpdate(BaseModel):
    road_id: Optional[UUID] = None
    timestamp: Optional[datetime] = None
    vehicle_count: Optional[int] = Field(default=None, ge=0)
    average_speed: Optional[float] = Field(default=None, ge=0)
    traffic_density: Optional[float] = Field(default=None, ge=0, le=100)
    congestion_level: Optional[str] = None
    road_condition: Optional[str] = None
    weather_condition: Optional[str] = None
    rainfall: Optional[float] = Field(default=None, ge=0)
    temperature: Optional[float] = None
    visibility: Optional[float] = Field(default=None, ge=0)
    is_holiday: Optional[bool] = None


class TrafficResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    traffic_id: UUID
    road_id: UUID
    road_name: Optional[str] = None
    timestamp: datetime
    vehicle_count: int
    average_speed: Optional[float] = None
    traffic_density: Optional[float] = None
    congestion_level: Optional[str] = None
    road_condition: Optional[str] = None
    weather_condition: Optional[str] = None
    rainfall: Optional[float] = None
    temperature: Optional[float] = None
    visibility: Optional[float] = None
    is_holiday: bool = False