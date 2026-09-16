from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

from app.database.connection import get_db
from app.database.models import TrafficZone
from app.schemas.traffic import ZoneCreate, ZoneResponse
from app.security import require_roles


router = APIRouter(
    prefix="/zones",
    tags=["Traffic Zones"]
)


def _format_zone_response(zone: TrafficZone) -> ZoneResponse:
    lat = None
    lon = None
    if zone.location is not None:
        point = to_shape(zone.location)
        lat = point.y
        lon = point.x

    return ZoneResponse(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        description=zone.description,
        latitude=lat,
        longitude=lon,
        created_at=zone.created_at
    )


# CREATE ZONE
@router.post(
    "",
    response_model=ZoneResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)
def create_zone(
    zone: ZoneCreate,
    db: Session = Depends(get_db)
):
    location = WKTElement(
        f"POINT({zone.longitude} {zone.latitude})",
        srid=4326
    )

    db_zone = TrafficZone(
        zone_name=zone.zone_name,
        description=zone.description,
        location=location
    )

    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)

    return _format_zone_response(db_zone)


# GET ALL ZONES
@router.get("", response_model=list[ZoneResponse])
def get_zones(
    db: Session = Depends(get_db)
):
    zones = db.query(TrafficZone).all()
    return [_format_zone_response(zone) for zone in zones]


# GET ONE ZONE
@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(
    zone_id: UUID,
    db: Session = Depends(get_db)
):
    zone = (
        db.query(TrafficZone)
        .filter(TrafficZone.zone_id == zone_id)
        .first()
    )

    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Traffic zone with ID '{zone_id}' does not exist. Please check the zone ID and try again."
        )

    return _format_zone_response(zone)


# UPDATE ZONE
@router.put(
    "/{zone_id}",
    response_model=ZoneResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)
def update_zone(
    zone_id: UUID,
    zone: ZoneCreate,
    db: Session = Depends(get_db)
):
    db_zone = (
        db.query(TrafficZone)
        .filter(TrafficZone.zone_id == zone_id)
        .first()
    )

    if not db_zone:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update: Traffic zone with ID '{zone_id}' does not exist."
        )

    db_zone.zone_name = zone.zone_name
    db_zone.description = zone.description

    db_zone.location = WKTElement(
        f"POINT({zone.longitude} {zone.latitude})",
        srid=4326
    )

    db.commit()
    db.refresh(db_zone)

    return _format_zone_response(db_zone)


# DELETE ZONE
@router.delete(
    "/{zone_id}",
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)
def delete_zone(
    zone_id: UUID,
    db: Session = Depends(get_db)
):
    db_zone = (
        db.query(TrafficZone)
        .filter(TrafficZone.zone_id == zone_id)
        .first()
    )

    if not db_zone:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot delete: Traffic zone with ID '{zone_id}' does not exist."
        )

    db.delete(db_zone)
    db.commit()

    return {
        "message": "Traffic zone deleted successfully"
    }