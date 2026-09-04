from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import Accident, Road
from app.schemas.accident import (
    AccidentCreate,
    AccidentResponse
)
from app.security import get_current_user


router = APIRouter(
    prefix="/api/accidents",
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
@router.post("/", response_model=AccidentResponse)
def create_accident(
    accident: AccidentCreate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
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
            detail="Road not found"
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
        created_by=current_user_id
    )

    db.add(db_accident)
    db.commit()
    db.refresh(db_accident)

    return _format_accident_response(db_accident)


# GET ALL ACCIDENTS
@router.get("/", response_model=list[AccidentResponse])
def get_accidents(
    db: Session = Depends(get_db)
):

    accidents = db.query(Accident).all()
    return [_format_accident_response(accident) for accident in accidents]


# GET ACCIDENT BY ID
@router.get(
    "/{accident_id}",
    response_model=AccidentResponse
)
def get_accident(
    accident_id: int,
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
            detail="Accident not found"
        )

    return _format_accident_response(accident)