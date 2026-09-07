from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WeatherCreate(BaseModel):
    road_id: UUID
    timestamp: datetime
    temperature: float | None = None
    rainfall: float | None = Field(default=None, ge=0)
    humidity: float | None = Field(default=None, ge=0, le=100)
    visibility: float | None = Field(default=None, ge=0)
    wind_speed: float | None = Field(default=None, ge=0)
    weather_condition: str | None = None


class WeatherUpdate(BaseModel):
    road_id: UUID | None = None
    timestamp: datetime | None = None
    temperature: float | None = None
    rainfall: float | None = Field(default=None, ge=0)
    humidity: float | None = Field(default=None, ge=0, le=100)
    visibility: float | None = Field(default=None, ge=0)
    wind_speed: float | None = Field(default=None, ge=0)
    weather_condition: str | None = None


class WeatherResponse(BaseModel):
    weather_id: UUID
    road_id: UUID
    timestamp: datetime
    temperature: float | None = None
    rainfall: float | None = None
    humidity: float | None = None
    visibility: float | None = None
    wind_speed: float | None = None
    weather_condition: str | None = None

    class Config:
        from_attributes = True
