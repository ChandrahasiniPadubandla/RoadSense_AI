from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DashboardStatsResponse(BaseModel):
    active_roads: int
    total_roads: int
    high_traffic_roads: int
    accident_alerts: int
    high_risk_zones: int
    total_accidents: int
    accidents_today: int
    total_traffic_records: int
    average_system_speed: Optional[float] = None
    timestamp: datetime

    class Config:
        from_attributes = True
