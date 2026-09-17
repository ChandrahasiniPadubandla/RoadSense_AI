from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import AuditLog
from app.schemas.audit import AuditLogCreate, AuditLogResponse, AuditLogUpdate
from app.security import get_current_user, require_roles


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)


@router.post("", response_model=AuditLogResponse)
def create_audit_log(
    audit_data: AuditLogCreate,
    request: Request,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    values = audit_data.model_dump()
    values["user_id"] = user_id
    values["timestamp"] = values["timestamp"] or datetime.now(timezone.utc)
    if values["ip_address"] is None and request.client:
        values["ip_address"] = request.client.host

    record = AuditLog(**values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(log_id: UUID, db: Session = Depends(get_db)):
    record = db.query(AuditLog).filter(AuditLog.log_id == log_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Audit log entry with ID '{log_id}' does not exist."
        )
    return record


@router.put("/{log_id}", response_model=AuditLogResponse)
def update_audit_log(
    log_id: UUID,
    audit_data: AuditLogUpdate,
    db: Session = Depends(get_db)
):
    record = db.query(AuditLog).filter(AuditLog.log_id == log_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update: Audit log entry with ID '{log_id}' does not exist."
        )

    for field, value in audit_data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{log_id}")
def delete_audit_log(log_id: UUID, db: Session = Depends(get_db)):
    record = db.query(AuditLog).filter(AuditLog.log_id == log_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot delete: Audit log entry with ID '{log_id}' does not exist."
        )

    db.delete(record)
    db.commit()
    return {"message": "Audit log deleted successfully"}