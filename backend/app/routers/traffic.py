from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.database.models import (
    TrafficRecord,
    Road
)

from app.schemas.traffic import (
    TrafficCreate,
    TrafficUpdate,
    TrafficResponse
)
from app.security import require_roles


router = APIRouter(
    prefix="/traffic",
    tags=["Traffic"]
)


@router.post(
    "",
    response_model=TrafficResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
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
            detail=f"Cannot record traffic: Road with ID '{traffic.road_id}' does not exist. Please verify the road ID."
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
    traffic_id: UUID,
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
            detail=f"Traffic record with ID '{traffic_id}' does not exist."
        )

    return record

@router.get(
    "/road/{road_id}",
    response_model=list[TrafficResponse]
)
def get_road_traffic(
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
            detail=f"Road with ID '{road_id}' does not exist. Cannot retrieve traffic data."
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


# UPDATE TRAFFIC RECORD
@router.put(
    "/{traffic_id}",
    response_model=TrafficResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def update_traffic_record(
    traffic_id: UUID,
    traffic_data: TrafficUpdate,
    db: Session = Depends(get_db)
):
    record = (
        db.query(TrafficRecord)
        .filter(TrafficRecord.traffic_id == traffic_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update: Traffic record with ID '{traffic_id}' does not exist."
        )

    if traffic_data.road_id is not None:
        road = (
            db.query(Road)
            .filter(Road.road_id == traffic_data.road_id)
            .first()
        )
        if not road:
            raise HTTPException(
                status_code=404,
                detail=f"Cannot link traffic record: Road with ID '{traffic_data.road_id}' does not exist."
            )
        record.road_id = traffic_data.road_id

    if traffic_data.timestamp is not None:
        record.timestamp = traffic_data.timestamp

    if traffic_data.vehicle_count is not None:
        record.vehicle_count = traffic_data.vehicle_count

    if traffic_data.average_speed is not None:
        record.average_speed = traffic_data.average_speed

    if traffic_data.traffic_density is not None:
        record.traffic_density = traffic_data.traffic_density

    if traffic_data.congestion_level is not None:
        record.congestion_level = traffic_data.congestion_level

    if traffic_data.road_condition is not None:
        record.road_condition = traffic_data.road_condition

    if traffic_data.weather_condition is not None:
        record.weather_condition = traffic_data.weather_condition

    if traffic_data.rainfall is not None:
        record.rainfall = traffic_data.rainfall

    if traffic_data.temperature is not None:
        record.temperature = traffic_data.temperature

    if traffic_data.visibility is not None:
        record.visibility = traffic_data.visibility

    if traffic_data.is_holiday is not None:
        record.is_holiday = traffic_data.is_holiday

    db.commit()
    db.refresh(record)

    return record


# DELETE TRAFFIC RECORD
@router.delete(
    "/{traffic_id}",
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)
def delete_traffic_record(
    traffic_id: UUID,
    db: Session = Depends(get_db)
):
    record = (
        db.query(TrafficRecord)
        .filter(TrafficRecord.traffic_id == traffic_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot delete: Traffic record with ID '{traffic_id}' does not exist."
        )

    db.delete(record)
    db.commit()

    return {
        "message": "Traffic record deleted successfully"
    }