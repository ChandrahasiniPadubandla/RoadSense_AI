from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Road

from app.schemas.traffic import (
    RoadCreate,
    RoadResponse
)


router = APIRouter(
    prefix="/api/roads",
    tags=["Roads"]
)


@router.post(
    "",
    response_model=RoadResponse
)
def create_road(
    road: RoadCreate,
    db: Session = Depends(get_db)
):

    new_road = Road(
        zone_id=road.zone_id,
        road_name=road.road_name,
        road_type=road.road_type,
        road_capacity=road.road_capacity,
        speed_limit=road.speed_limit,
        road_condition=road.road_condition,
        number_of_lanes=road.number_of_lanes
    )

    db.add(new_road)

    db.commit()

    db.refresh(new_road)

    return new_road


@router.get(
    "",
    response_model=list[RoadResponse]
)
def get_roads(
    db: Session = Depends(get_db)
):

    return db.query(Road).all()


@router.get(
    "/{road_id}",
    response_model=RoadResponse
)
def get_road(
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

    return road


@router.put(
    "/{road_id}",
    response_model=RoadResponse
)
def update_road(
    road_id: int,
    road: RoadCreate,
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
            detail="Road not found"
        )

    db_road.zone_id = road.zone_id
    db_road.road_name = road.road_name
    db_road.road_type = road.road_type
    db_road.road_capacity = road.road_capacity
    db_road.speed_limit = road.speed_limit
    db_road.road_condition = road.road_condition
    db_road.number_of_lanes = road.number_of_lanes

    db.commit()
    db.refresh(db_road)

    return db_road


@router.delete("/{road_id}")
def delete_road(
    road_id: int,
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
            detail="Road not found"
        )

    db.delete(db_road)
    db.commit()

    return {
        "message": "Road deleted successfully"
    }