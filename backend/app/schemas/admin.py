from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: UUID
    role_name: str
    description: Optional[str] = None


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    role_id: UUID
    role_name: Optional[str] = None
    name: str
    email: EmailStr
    phone: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserRoleUpdate(BaseModel):
    role_id: UUID


class UserStatusUpdate(BaseModel):
    is_active: bool
