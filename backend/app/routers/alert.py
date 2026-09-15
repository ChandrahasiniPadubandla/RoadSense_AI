from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Alert
from app.security import require_roles


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class AlertCreateRequest(BaseModel):
    road_id: UUID | None = None
    prediction_id: UUID | None = None
    alert_type: str
    severity: str
    message: str


class AlertUpdateRequest(BaseModel):
    road_id: UUID | None = None
    prediction_id: UUID | None = None
    alert_type: str | None = None
    severity: str | None = None
    message: str | None = None
    status: str | None = None
    resolved_at: datetime | None = None


# ============================================================
# SERIALIZER
# ============================================================

def _serialize_alert(alert: Alert):
    return {
        "alert_id": str(alert.alert_id),
        "road_id": str(alert.road_id) if alert.road_id else None,
        "prediction_id": str(alert.prediction_id) if alert.prediction_id else None,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "created_at": (
            alert.created_at.isoformat()
            if alert.created_at
            else None
        ),
        "status": alert.status,
        "resolved_at": (
            alert.resolved_at.isoformat()
            if alert.resolved_at
            else None
        ),
    }


# ============================================================
# CREATE
# ============================================================

@router.post(
    "",
    summary="Create a new accident alert",
    status_code=201,
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def create_alert(
    alert_data: AlertCreateRequest,
    db: Session = Depends(get_db)
):
    alert = Alert(
        road_id=alert_data.road_id,
        prediction_id=alert_data.prediction_id,
        alert_type=alert_data.alert_type,
        severity=alert_data.severity,
        message=alert_data.message,
        status="ACTIVE",
        created_at=datetime.now(timezone.utc)
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return _serialize_alert(alert)


# ============================================================
# READ - GET ALL ALERTS
# ============================================================

@router.get(
    "",
    summary="Get accident alerts from the database"
)
def get_alerts(
    road_id: UUID | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)

    if road_id is not None:
        query = query.filter(Alert.road_id == road_id)

    if severity:
        query = query.filter(
            Alert.severity.ilike(f"%{severity}%")
        )

    if status:
        query = query.filter(
            Alert.status.ilike(f"%{status}%")
        )

    alerts = (
        query
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )

    return [_serialize_alert(alert) for alert in alerts]


# ============================================================
# READ - GET ONE ALERT
# ============================================================

@router.get(
    "/{alert_id}",
    summary="Get a single alert by ID"
)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert with ID '{alert_id}' was not found."
        )

    return _serialize_alert(alert)


# ============================================================
# UPDATE
# ============================================================

@router.patch(
    "/{alert_id}",
    summary="Update an alert",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY", "EMERGENCY_RESPONSE"))]
)
def update_alert(
    alert_id: UUID,
    alert_update: AlertUpdateRequest,
    db: Session = Depends(get_db)
):
    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert with ID '{alert_id}' was not found."
        )

    # Update only fields that were actually provided
    if alert_update.road_id is not None:
        alert.road_id = alert_update.road_id

    if alert_update.prediction_id is not None:
        alert.prediction_id = alert_update.prediction_id

    if alert_update.alert_type is not None:
        alert.alert_type = alert_update.alert_type

    if alert_update.severity is not None:
        alert.severity = alert_update.severity

    if alert_update.message is not None:
        alert.message = alert_update.message

    if alert_update.status is not None:
        alert.status = alert_update.status.upper()

    if alert_update.resolved_at is not None:
        alert.resolved_at = alert_update.resolved_at

    # Automatically set resolved_at when status becomes RESOLVED
    elif (
        alert.status
        and alert.status.upper() == "RESOLVED"
        and alert.resolved_at is None
    ):
        alert.resolved_at = datetime.now(timezone.utc)

    # If alert is changed from RESOLVED to another status,
    # clear the resolved timestamp.
    if (
        alert.status
        and alert.status.upper() != "RESOLVED"
        and alert_update.status is not None
        and alert_update.resolved_at is None
    ):
        alert.resolved_at = None

    db.commit()
    db.refresh(alert)

    return _serialize_alert(alert)


# ============================================================
# DELETE
# ============================================================

@router.delete(
    "/{alert_id}",
    summary="Delete an alert",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def delete_alert(
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert with ID '{alert_id}' was not found."
        )

    db.delete(alert)
    db.commit()

    return {
        "message": "Alert deleted successfully.",
        "alert_id": str(alert_id)
    }
