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


router = APIRouter(
    prefix="/api/accidents",
    tags=["Accidents"]
)


# CREATE ACCIDENT
@router.post("/", response_model=AccidentResponse)
def create_accident(
    accident: AccidentCreate,
    db: Session = Depends(get_db)
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
        accident_time=accident.accident_time,
        weather_condition=accident.weather_condition,
        road_condition=accident.road_condition,
        vehicle_count=accident.vehicle_count,
        severity=accident.severity,
        fatalities=accident.fatalities,
        injuries=accident.injuries,
        description=accident.description
    )

    db.add(db_accident)
    db.commit()
    db.refresh(db_accident)

    point = to_shape(db_accident.location)

    return AccidentResponse(
        accident_id=db_accident.accident_id,
        road_id=db_accident.road_id,
        latitude=point.y,
        longitude=point.x,
        accident_time=db_accident.accident_time,
        weather_condition=db_accident.weather_condition,
        road_condition=db_accident.road_condition,
        vehicle_count=db_accident.vehicle_count,
        severity=db_accident.severity,
        fatalities=db_accident.fatalities,
        injuries=db_accident.injuries,
        description=db_accident.description,
        created_by=db_accident.created_by,
        created_at=db_accident.created_at
    )


# GET ALL ACCIDENTS
@router.get("/", response_model=list[AccidentResponse])
def get_accidents(
    db: Session = Depends(get_db)
):

    accidents = db.query(Accident).all()

    result = []

    for accident in accidents:

        point = to_shape(accident.location)

        result.append(
            AccidentResponse(
                accident_id=accident.accident_id,
                road_id=accident.road_id,
                latitude=point.y,
                longitude=point.x,
                accident_time=accident.accident_time,
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
        )

    return result


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

    point = to_shape(accident.location)

    return AccidentResponse(
        accident_id=accident.accident_id,
        road_id=accident.road_id,
        latitude=point.y,
        longitude=point.x,
        accident_time=accident.accident_time,
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