from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import Accident, Road, User
from app.schemas.accident import (
    AccidentCreate,
    AccidentUpdate,
    AccidentResponse
)
from app.security import require_roles


router = APIRouter(
    prefix="/accidents",
    tags=["Accidents"]
)


def _format_accident_response(accident: Accident) -> AccidentResponse:
    lat = None
    lon = None
    if accident.location is not None:
        point = to_shape(accident.location)
        lat = point.y
        lon = point.x

    return AccidentResponse(
        accident_id=accident.accident_id,
        road_id=accident.road_id,
        latitude=lat,
        longitude=lon,
        accident_time=getattr(accident, "accident_datetime", None) or getattr(accident, "accident_time", None),
        weather_condition=accident.weather_condition,
        road_condition=accident.road_condition,
        vehicle_count=accident.vehicle_count,
        severity=accident.severity,
        fatalities=accident.fatalities,
        injuries=accident.injuries,
        description=accident.description,
        created_by=accident.created_by,
        created_at=accident.created_at
    )


# CREATE ACCIDENT
@router.post("", response_model=AccidentResponse)
def create_accident(
    accident: AccidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))
):

    # Check whether road exists
    road = (
        db.query(Road)
        .filter(Road.road_id == accident.road_id)
        .first()
    )

    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot record accident: Road with ID '{accident.road_id}' does not exist. Please verify the road ID."
        )

    # Convert latitude/longitude to PostGIS POINT
    location = WKTElement(
        f"POINT({accident.longitude} {accident.latitude})",
        srid=4326
    )

    db_accident = Accident(
        road_id=accident.road_id,
        location=location,
        accident_datetime=accident.accident_time,
        weather_condition=accident.weather_condition,
        road_condition=accident.road_condition,
        vehicle_count=accident.vehicle_count,
        severity=accident.severity,
        fatalities=accident.fatalities,
        injuries=accident.injuries,
        description=accident.description,
        created_by=current_user.user_id
    )

    db.add(db_accident)
    db.commit()
    db.refresh(db_accident)

    return _format_accident_response(db_accident)


# GET ALL ACCIDENTS
@router.get("", response_model=list[AccidentResponse])
def get_all_accidents(
    db: Session = Depends(get_db)
):

    accidents = db.query(Accident).all()
    return [_format_accident_response(accident) for accident in accidents]


# GET ACCIDENTS BY ROAD ID
@router.get(
    "/road/{road_id}",
    response_model=list[AccidentResponse]
)
def get_accidents_by_road(
    road_id: UUID,
    db: Session = Depends(get_db)
):
    road = (
        db.query(Road)
        .filter(Road.road_id == road_id)
        .first()
    )

    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Road with ID '{road_id}' does not exist. Cannot retrieve accident history."
        )

    accidents = (
        db.query(Accident)
        .filter(Accident.road_id == road_id)
        .order_by(Accident.accident_datetime.desc())
        .all()
    )

    return [_format_accident_response(accident) for accident in accidents]


# GET ACCIDENT BY ID
@router.get(
    "/{accident_id}",
    response_model=AccidentResponse
)
def get_accident(
    accident_id: UUID,
    db: Session = Depends(get_db)
):

    accident = (
        db.query(Accident)
        .filter(
            Accident.accident_id == accident_id
        )
        .first()
    )

    if not accident:
        raise HTTPException(
            status_code=404,
            detail=f"Accident record with ID '{accident_id}' does not exist."
        )

    return _format_accident_response(accident)


# UPDATE ACCIDENT
@router.put(
    "/{accident_id}",
    response_model=AccidentResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def update_accident(
    accident_id: UUID,
    accident_data: AccidentUpdate,
    db: Session = Depends(get_db)
):
    db_accident = (
        db.query(Accident)
        .filter(Accident.accident_id == accident_id)
        .first()
    )

    if not db_accident:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update: Accident record with ID '{accident_id}' does not exist."
        )

    if accident_data.road_id is not None:
        road = (
            db.query(Road)
            .filter(Road.road_id == accident_data.road_id)
            .first()
        )
        if not road:
            raise HTTPException(
                status_code=404,
                detail=f"Cannot link accident: Road with ID '{accident_data.road_id}' does not exist."
            )
        db_accident.road_id = accident_data.road_id

    if accident_data.latitude is not None and accident_data.longitude is not None:
        db_accident.location = WKTElement(
            f"POINT({accident_data.longitude} {accident_data.latitude})",
            srid=4326
        )

    if accident_data.accident_time is not None:
        db_accident.accident_datetime = accident_data.accident_time

    if accident_data.weather_condition is not None:
        db_accident.weather_condition = accident_data.weather_condition

    if accident_data.road_condition is not None:
        db_accident.road_condition = accident_data.road_condition

    if accident_data.vehicle_count is not None:
        db_accident.vehicle_count = accident_data.vehicle_count

    if accident_data.severity is not None:
        db_accident.severity = accident_data.severity

    if accident_data.fatalities is not None:
        db_accident.fatalities = accident_data.fatalities

    if accident_data.injuries is not None:
        db_accident.injuries = accident_data.injuries

    if accident_data.description is not None:
        db_accident.description = accident_data.description

    db.commit()
    db.refresh(db_accident)

    return _format_accident_response(db_accident)


# DELETE ACCIDENT
@router.delete(
    "/{accident_id}",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def delete_accident(
    accident_id: UUID,
    db: Session = Depends(get_db)
):
    db_accident = (
        db.query(Accident)
        .filter(Accident.accident_id == accident_id)
        .first()
    )

    if not db_accident:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot delete: Accident record with ID '{accident_id}' does not exist."
        )

    db.delete(db_accident)
    db.commit()

    return {
        "message": "Accident record deleted successfully"
    }