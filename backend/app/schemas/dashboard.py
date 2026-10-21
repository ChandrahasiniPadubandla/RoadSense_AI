from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DashboardStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
