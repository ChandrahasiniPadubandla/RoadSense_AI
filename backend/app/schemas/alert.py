from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AlertResponse(BaseModel):
    alert_id: UUID
    road_id: Optional[UUID] = None
    prediction_id: Optional[UUID] = None
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertUpdateRequest(BaseModel):
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None
