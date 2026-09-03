from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

from app.database.connection import get_db
from app.database.models import TrafficZone
from app.schemas.traffic import ZoneCreate, ZoneResponse


router = APIRouter(
    prefix="/api/zones",
    tags=["Traffic Zones"]
)


# CREATE ZONE
@router.post("/", response_model=ZoneResponse)
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

    point = to_shape(db_zone.location)

    return ZoneResponse(
        zone_id=db_zone.zone_id,
        zone_name=db_zone.zone_name,
        description=db_zone.description,
        latitude=point.y,
        longitude=point.x,
        created_at=db_zone.created_at
    )


# GET ALL ZONES
@router.get("/", response_model=list[ZoneResponse])
def get_zones(
    db: Session = Depends(get_db)
):
    zones = db.query(TrafficZone).all()

    result = []

    for zone in zones:
        point = to_shape(zone.location)

        result.append(
            ZoneResponse(
                zone_id=zone.zone_id,
                zone_name=zone.zone_name,
                description=zone.description,
                latitude=point.y,
                longitude=point.x,
                created_at=zone.created_at
            )
        )

    return result


# GET ONE ZONE
@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(
    zone_id: int,
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
            detail="Traffic zone not found"
        )

    point = to_shape(zone.location)

    return ZoneResponse(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        description=zone.description,
        latitude=point.y,
        longitude=point.x,
        created_at=zone.created_at
    )


# UPDATE ZONE
@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: int,
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
            detail="Traffic zone not found"
        )

    db_zone.zone_name = zone.zone_name
    db_zone.description = zone.description

    db_zone.location = WKTElement(
        f"POINT({zone.longitude} {zone.latitude})",
        srid=4326
    )

    db.commit()
    db.refresh(db_zone)

    point = to_shape(db_zone.location)

    return ZoneResponse(
        zone_id=db_zone.zone_id,
        zone_name=db_zone.zone_name,
        description=db_zone.description,
        latitude=point.y,
        longitude=point.x,
        created_at=db_zone.created_at
    )


# DELETE ZONE
@router.delete("/{zone_id}")
def delete_zone(
    zone_id: int,
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
            detail="Traffic zone not found"
        )

    db.delete(db_zone)
    db.commit()

    return {
        "message": "Traffic zone deleted successfully"
    }