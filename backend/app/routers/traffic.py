from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.database.models import (
    TrafficRecord,
    Road
)

from app.schemas.traffic import (
    TrafficCreate,
    TrafficResponse
)


router = APIRouter(
    prefix="/api/traffic",
    tags=["Traffic Management"]
)


@router.post(
    "",
    response_model=TrafficResponse
)
def create_traffic_record(
    traffic: TrafficCreate,
    db: Session = Depends(get_db)
):

    # Check whether road exists

    road = (
        db.query(Road)
        .filter(
            Road.road_id == traffic.road_id
        )
        .first()
    )

    if not road:

        raise HTTPException(
            status_code=404,
            detail="Road not found"
        )

    new_record = TrafficRecord(
        road_id=traffic.road_id,
        timestamp=traffic.timestamp,
        vehicle_count=traffic.vehicle_count,
        average_speed=traffic.average_speed,
        traffic_density=traffic.traffic_density,
        congestion_level=traffic.congestion_level,
        road_condition=traffic.road_condition,
        weather_condition=traffic.weather_condition,
        rainfall=traffic.rainfall,
        temperature=traffic.temperature,
        visibility=traffic.visibility,
        is_holiday=traffic.is_holiday
    )

    db.add(new_record)

    db.commit()

    db.refresh(new_record)

    return new_record


@router.get(
    "",
    response_model=list[TrafficResponse]
)
def get_traffic_records(
    db: Session = Depends(get_db)
):

    return (
        db.query(TrafficRecord)
        .order_by(
            TrafficRecord.timestamp.desc()
        )
        .all()
    )


@router.get(
    "/{traffic_id}",
    response_model=TrafficResponse
)
def get_traffic_record(
    traffic_id: int,
    db: Session = Depends(get_db)
):

    record = (
        db.query(TrafficRecord)
        .filter(
            TrafficRecord.traffic_id == traffic_id
        )
        .first()
    )

    if not record:

        raise HTTPException(
            status_code=404,
            detail="Traffic record not found"
        )

    return record

@router.get(
    "/road/{road_id}",
    response_model=list[TrafficResponse]
)
def get_road_traffic(
    road_id: int,
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
            detail="Road not found"
        )

    records = (
        db.query(TrafficRecord)
        .filter(
            TrafficRecord.road_id == road_id
        )
        .order_by(
            TrafficRecord.timestamp.desc()
        )
        .all()
    )

    return records