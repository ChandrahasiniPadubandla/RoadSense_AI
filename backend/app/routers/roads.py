from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import Road, TrafficZone

from app.schemas.traffic import (
    RoadCreate,
    RoadUpdate,
    RoadResponse
)


router = APIRouter(
    prefix="/api/roads",
    tags=["Roads"]
)


def _format_road_response(road: Road) -> RoadResponse:
    start_lat = None
    start_lon = None
    if road.start_location is not None:
        p = to_shape(road.start_location)
        start_lat = p.y
        start_lon = p.x

    end_lat = None
    end_lon = None
    if road.end_location is not None:
        p = to_shape(road.end_location)
        end_lat = p.y
        end_lon = p.x

    return RoadResponse(
        road_id=road.road_id,
        zone_id=road.zone_id,
        road_name=road.road_name,
        road_type=road.road_type,
        start_latitude=start_lat,
        start_longitude=start_lon,
        end_latitude=end_lat,
        end_longitude=end_lon,
        road_capacity=road.road_capacity,
        speed_limit=float(road.speed_limit) if road.speed_limit is not None else None,
        road_condition=road.road_condition,
        number_of_lanes=road.number_of_lanes,
        is_active=road.is_active,
        created_at=road.created_at
    )


@router.post(
    "",
    response_model=RoadResponse
)
def create_road(
    road: RoadCreate,
    db: Session = Depends(get_db)
):
    if road.zone_id is not None:
        zone = db.query(TrafficZone).filter(TrafficZone.zone_id == road.zone_id).first()
        if not zone:
            raise HTTPException(
                status_code=404,
                detail=f"Traffic zone with ID '{road.zone_id}' does not exist. Please specify a valid zone."
            )

    start_location = None
    if road.start_latitude is not None and road.start_longitude is not None:
        start_location = WKTElement(
            f"POINT({road.start_longitude} {road.start_latitude})",
            srid=4326
        )

    end_location = None
    if road.end_latitude is not None and road.end_longitude is not None:
        end_location = WKTElement(
            f"POINT({road.end_longitude} {road.end_latitude})",
            srid=4326
        )

    new_road = Road(
        zone_id=road.zone_id,
        road_name=road.road_name,
        road_type=road.road_type,
        start_location=start_location,
        end_location=end_location,
        road_capacity=road.road_capacity,
        speed_limit=road.speed_limit,
        road_condition=road.road_condition,
        number_of_lanes=road.number_of_lanes,
        is_active=road.is_active if road.is_active is not None else True
    )

    db.add(new_road)
    db.commit()
    db.refresh(new_road)

    return _format_road_response(new_road)


@router.get(
    "",
    response_model=list[RoadResponse]
)
def get_roads(
    db: Session = Depends(get_db)
):
    roads = db.query(Road).all()
    return [_format_road_response(road) for road in roads]


@router.get(
    "/{road_id}",
    response_model=RoadResponse
)
def get_road(
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
            detail=f"Road with ID '{road_id}' does not exist. Please verify the road ID."
        )

    return _format_road_response(road)


@router.put(
    "/{road_id}",
    response_model=RoadResponse
)
def update_road(
    road_id: UUID,
    road: RoadUpdate,
    db: Session = Depends(get_db)
):
    db_road = (
        db.query(Road)
        .filter(Road.road_id == road_id)
        .first()
    )

    if not db_road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update: Road with ID '{road_id}' does not exist."
        )

    if road.zone_id is not None:
        zone = db.query(TrafficZone).filter(TrafficZone.zone_id == road.zone_id).first()
        if not zone:
            raise HTTPException(
                status_code=404,
                detail=f"Traffic zone with ID '{road.zone_id}' does not exist. Cannot link road to invalid zone."
            )
        db_road.zone_id = road.zone_id
    if road.road_name is not None:
        db_road.road_name = road.road_name
    if road.road_type is not None:
        db_road.road_type = road.road_type
    if road.start_latitude is not None and road.start_longitude is not None:
        db_road.start_location = WKTElement(
            f"POINT({road.start_longitude} {road.start_latitude})",
            srid=4326
        )
    if road.end_latitude is not None and road.end_longitude is not None:
        db_road.end_location = WKTElement(
            f"POINT({road.end_longitude} {road.end_latitude})",
            srid=4326
        )
    if road.road_capacity is not None:
        db_road.road_capacity = road.road_capacity
    if road.speed_limit is not None:
        db_road.speed_limit = road.speed_limit
    if road.road_condition is not None:
        db_road.road_condition = road.road_condition
    if road.number_of_lanes is not None:
        db_road.number_of_lanes = road.number_of_lanes
    if road.is_active is not None:
        db_road.is_active = road.is_active

    db.commit()
    db.refresh(db_road)

    return _format_road_response(db_road)


@router.delete("/{road_id}")
def delete_road(
    road_id: UUID,
    db: Session = Depends(get_db)
):
    db_road = (
        db.query(Road)
        .filter(Road.road_id == road_id)
        .first()
    )

    if not db_road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot delete: Road with ID '{road_id}' does not exist."
        )

    db.delete(db_road)
    db.commit()

    return {
        "message": "Road deleted successfully"
    }