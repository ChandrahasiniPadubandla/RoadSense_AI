from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Accident,
    AuthOTP,
    AuditLog,
    EmergencyResponse,
    User,
    Role,
)
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


@router.patch("/users/{username}/role", response_model=UserAdminResponse, summary="Change a user's system role")
def update_user_role(
    username: str = Path(..., description="The user's name used as the username"),
    role_update: UserRoleUpdate = Body(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.name == username).first()
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


@router.patch("/users/{username}/status", response_model=UserAdminResponse, summary="Activate or deactivate a user")
def update_user_status(
    username: str = Path(..., description="The user's name used as the username"),
    status_update: UserStatusUpdate = Body(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = status_update.is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _format_user(user)


@router.delete("/users/{username}", summary="Delete a user permanently")
def delete_user(
    username: str = Path(..., description="The user's name used as the username"),
    current_user: User = Depends(require_roles("SUPER_ADMIN")),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=400,
            detail="A super admin cannot delete their own account"
        )

    db.query(AuthOTP).filter(AuthOTP.user_id == user.user_id).delete(
        synchronize_session=False
    )
    db.query(AuditLog).filter(AuditLog.user_id == user.user_id).delete(
        synchronize_session=False
    )
    db.query(Accident).filter(Accident.created_by == user.user_id).update(
        {Accident.created_by: None},
        synchronize_session=False
    )
    db.query(EmergencyResponse).filter(
        EmergencyResponse.assigned_user_id == user.user_id
    ).update(
        {EmergencyResponse.assigned_user_id: None},
        synchronize_session=False
    )
    db.add(AuditLog(
        user_id=current_user.user_id,
        action="DELETE",
        entity_type="user",
        entity_id=user.user_id,
        details=f"Deleted user {user.email}"
    ))
    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully", "username": username}
