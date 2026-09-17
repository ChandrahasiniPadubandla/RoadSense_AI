from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class RoleResponse(BaseModel):
    role_id: UUID
    role_name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserAdminResponse(BaseModel):
    user_id: UUID
    role_id: UUID
    role_name: Optional[str] = None
    name: str
    email: EmailStr
    phone: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role_id: UUID


class UserStatusUpdate(BaseModel):
    is_active: bool
