from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User, Role
from app.security import require_roles
from app.schemas.admin import (
    UserAdminResponse,
    RoleResponse,
    UserRoleUpdate,
    UserStatusUpdate
)


router = APIRouter(
    prefix="/api/admin",
    tags=["Administration (Super Admin Only)"],
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)


def _format_user(user: User) -> UserAdminResponse:
    role_name = user.role.role_name if user.role else None
    return UserAdminResponse(
        user_id=user.user_id,
        role_id=user.role_id,
        role_name=role_name,
        name=user.name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/roles", response_model=list[RoleResponse], summary="List all available system roles")
def get_roles(
    db: Session = Depends(get_db)
):
    roles = db.query(Role).all()
    return roles


@router.get("/users", response_model=list[UserAdminResponse], summary="List all registered system users")
def get_all_users(
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return [_format_user(u) for u in users]


@router.patch("/users/{user_id}/role", response_model=UserAdminResponse, summary="Change a user's system role")
def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(Role).filter(Role.role_id == role_update.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Target role not found")

    user.role_id = role_update.role_id
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _format_user(user)


@router.patch("/users/{user_id}/status", response_model=UserAdminResponse, summary="Activate or deactivate a user")
def update_user_status(
    user_id: UUID,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = status_update.is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _format_user(user)
