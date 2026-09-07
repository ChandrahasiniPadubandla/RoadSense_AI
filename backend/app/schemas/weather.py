from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WeatherResponse(BaseModel):
    weather_id: UUID
    road_id: UUID
    timestamp: datetime
    temperature: Optional[float] = None
    rainfall: Optional[float] = None
    humidity: Optional[float] = None
    visibility: Optional[float] = None
    wind_speed: Optional[float] = None
    weather_condition: Optional[str] = None

    class Config:
        from_attributes = True
