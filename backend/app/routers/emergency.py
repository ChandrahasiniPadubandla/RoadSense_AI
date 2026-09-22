from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import EmergencyResponse, Accident, Road
from app.security import require_roles


router = APIRouter(
    prefix="/emergency",
    tags=["Emergency"]
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class EmergencyCreateRequest(BaseModel):
    accident_id: UUID
    assigned_user_id: UUID | None = None
    response_status: str | None = "PENDING"
    assigned_at: datetime | None = None
    arrived_at: datetime | None = None
    resolved_at: datetime | None = None
    notes: str | None = None


class EmergencyUpdateRequest(BaseModel):
    accident_id: UUID | None = None
    assigned_user_id: UUID | None = None
    response_status: str | None = None
    assigned_at: datetime | None = None
    arrived_at: datetime | None = None
    resolved_at: datetime | None = None
    notes: str | None = None


# ============================================================
# SERIALIZER
# ============================================================

def _serialize_emergency(emergency: EmergencyResponse, db: Session = None):
    accident_summary = None
    if db is not None and emergency.accident_id:
        row = (
            db.query(Accident, Road.road_name)
            .outerjoin(Road, Accident.road_id == Road.road_id)
            .filter(Accident.accident_id == emergency.accident_id)
            .first()
        )
        if row:
            accident, road_name = row
            accident_summary = {
                "road_name": road_name or "Unknown Road",
                "severity": accident.severity,
                "fatalities": accident.fatalities or 0,
                "injuries": accident.injuries or 0,
                "accident_datetime": accident.accident_datetime.isoformat() if accident.accident_datetime else None,
                "description": accident.description,
            }

    return {
        "response_id": str(emergency.response_id),

        "accident_id": (
            str(emergency.accident_id)
            if emergency.accident_id
            else None
        ),

        "accident": accident_summary,

        "assigned_user_id": (
            str(emergency.assigned_user_id)
            if emergency.assigned_user_id
            else None
        ),

        "response_status": emergency.response_status,

        "assigned_at": (
            emergency.assigned_at.isoformat()
            if emergency.assigned_at
            else None
        ),

        "arrived_at": (
            emergency.arrived_at.isoformat()
            if emergency.arrived_at
            else None
        ),

        "resolved_at": (
            emergency.resolved_at.isoformat()
            if emergency.resolved_at
            else None
        ),

        "notes": emergency.notes,
    }


# ============================================================
# CREATE
# ============================================================

@router.post(
    "",
    summary="Create a new emergency response",
    status_code=201,
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY", "EMERGENCY_RESPONSE"))]
)
def create_emergency(
    emergency_data: EmergencyCreateRequest,
    db: Session = Depends(get_db)
):
    # Check whether the accident exists
    from app.database.models import Accident

    accident = (
        db.query(Accident)
        .filter(
            Accident.accident_id == emergency_data.accident_id
        )
        .first()
    )

    if not accident:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Accident with ID "
                f"'{emergency_data.accident_id}' was not found."
            )
        )

    emergency = EmergencyResponse(
        accident_id=emergency_data.accident_id,
        assigned_user_id=emergency_data.assigned_user_id,
        response_status=(
            emergency_data.response_status.upper()
            if emergency_data.response_status
            else "PENDING"
        ),
        assigned_at=emergency_data.assigned_at,
        arrived_at=emergency_data.arrived_at,
        resolved_at=emergency_data.resolved_at,
        notes=emergency_data.notes
    )

    db.add(emergency)
    db.commit()
    db.refresh(emergency)

    return _serialize_emergency(emergency, db)


# ============================================================
# READ - GET ALL EMERGENCY RESPONSES
# ============================================================

@router.get(
    "",
    summary="Get all emergency responses"
)
def get_emergencies(
    accident_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    response_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(EmergencyResponse)

    if accident_id is not None:
        query = query.filter(
            EmergencyResponse.accident_id == accident_id
        )

    if assigned_user_id is not None:
        query = query.filter(
            EmergencyResponse.assigned_user_id == assigned_user_id
        )

    if response_status:
        query = query.filter(
            EmergencyResponse.response_status.ilike(
                f"%{response_status}%"
            )
        )

    emergencies = (
        query
        .order_by(EmergencyResponse.assigned_at.desc())
        .limit(limit)
        .all()
    )

    return [
        _serialize_emergency(emergency, db)
        for emergency in emergencies
    ]


# ============================================================
# READ - GET ONE EMERGENCY RESPONSE
# ============================================================

@router.get(
    "/{response_id}",
    summary="Get an emergency response by ID"
)
def get_emergency(
    response_id: UUID,
    db: Session = Depends(get_db)
):
    emergency = (
        db.query(EmergencyResponse)
        .filter(
            EmergencyResponse.response_id == response_id
        )
        .first()
    )

    if not emergency:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Emergency response with ID "
                f"'{response_id}' was not found."
            )
        )

    return _serialize_emergency(emergency, db)


# ============================================================
# UPDATE
# ============================================================

@router.patch(
    "/{response_id}",
    summary="Update an emergency response",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "EMERGENCY_RESPONSE"))]
)
def update_emergency(
    response_id: UUID,
    emergency_update: EmergencyUpdateRequest,
    db: Session = Depends(get_db)
):
    emergency = (
        db.query(EmergencyResponse)
        .filter(
            EmergencyResponse.response_id == response_id
        )
        .first()
    )

    if not emergency:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Emergency response with ID "
                f"'{response_id}' was not found."
            )
        )

    if emergency_update.accident_id is not None:
        emergency.accident_id = emergency_update.accident_id

    if emergency_update.assigned_user_id is not None:
        emergency.assigned_user_id = (
            emergency_update.assigned_user_id
        )

    if emergency_update.response_status is not None:
        emergency.response_status = (
            emergency_update.response_status.upper()
        )

    if emergency_update.assigned_at is not None:
        emergency.assigned_at = emergency_update.assigned_at

    if emergency_update.arrived_at is not None:
        emergency.arrived_at = emergency_update.arrived_at

    if emergency_update.resolved_at is not None:
        emergency.resolved_at = emergency_update.resolved_at

    if emergency_update.notes is not None:
        emergency.notes = emergency_update.notes

    # Automatically set resolved_at when status becomes RESOLVED
    if (
        emergency.response_status
        and emergency.response_status.upper() == "RESOLVED"
        and emergency.resolved_at is None
    ):
        emergency.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(emergency)

    return _serialize_emergency(emergency, db)


# ============================================================
# DELETE
# ============================================================

@router.delete(
    "/{response_id}",
    summary="Delete an emergency response",
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)
def delete_emergency(
    response_id: UUID,
    db: Session = Depends(get_db)
):
    emergency = (
        db.query(EmergencyResponse)
        .filter(
            EmergencyResponse.response_id == response_id
        )
        .first()
    )

    if not emergency:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Emergency response with ID "
                f"'{response_id}' was not found."
            )
        )

    db.delete(emergency)
    db.commit()

    return {
        "message": "Emergency response deleted successfully.",
        "response_id": str(response_id)
    }