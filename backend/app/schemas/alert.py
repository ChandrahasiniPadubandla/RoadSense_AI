from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: UUID
    road_id: Optional[UUID] = None
    prediction_id: Optional[UUID] = None
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AlertUpdateRequest(BaseModel):
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None
