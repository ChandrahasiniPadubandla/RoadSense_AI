from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AccidentCreate(BaseModel):

    road_id: int

    latitude: float = Field(
        ...,
        ge=-90,
        le=90
    )

    longitude: float = Field(
        ...,
        ge=-180,
        le=180
    )

    accident_time: datetime

    weather_condition: Optional[str] = None

    road_condition: Optional[str] = None

    vehicle_count: Optional[int] = Field(
        default=None,
        ge=0
    )

    severity: Optional[str] = None

    fatalities: int = Field(
        default=0,
        ge=0
    )

    injuries: int = Field(
        default=0,
        ge=0
    )

    description: Optional[str] = None


class AccidentResponse(BaseModel):

    accident_id: int

    road_id: int

    latitude: float

    longitude: float

    accident_time: datetime

    weather_condition: Optional[str] = None

    road_condition: Optional[str] = None

    vehicle_count: Optional[int] = None

    severity: Optional[str] = None

    fatalities: int

    injuries: int

    description: Optional[str] = None

    created_by: Optional[int] = None

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True