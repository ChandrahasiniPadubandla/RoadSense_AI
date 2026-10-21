from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class AuditLogCreate(BaseModel):
    action: str = Field(min_length=1, max_length=50)
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: UUID | None = None
    timestamp: datetime | None = None
    ip_address: str | None = Field(default=None, max_length=50)
    details: str | None = None


class AuditLogUpdate(BaseModel):
    action: str | None = Field(default=None, min_length=1, max_length=50)
    entity_type: str | None = Field(default=None, min_length=1, max_length=100)
    entity_id: UUID | None = None
    timestamp: datetime | None = None
    ip_address: str | None = Field(default=None, max_length=50)
    details: str | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: UUID
    user_id: UUID | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    timestamp: datetime | None = Field(default=None, exclude=True)
    ip_address: str | None = None
    details: str | None = None

    @computed_field
    @property
    def date(self) -> str | None:
        if self.timestamp is None:
            return None
        return f"{self.timestamp.day}-{self.timestamp.month}-{str(self.timestamp.year)[-2:]}"

    @computed_field
    @property
    def time(self) -> str | None:
        if self.timestamp is None:
            return None
        return self.timestamp.strftime("%I:%M %p").lstrip("0").lower()