import json
import urllib.request
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.security import require_roles


def fetch_osrm_linestring(
    start_lon: float, start_lat: float, end_lon: float, end_lat: float
) -> Optional[WKTElement]:
    """
    Calls OSRM public API to generate a driving route LINESTRING WKTElement.
    Falls back gracefully to a 2-point LINESTRING if OSRM is unreachable.
    """
    url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "Metrivon-AI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "routes" in data and len(data["routes"]) > 0:
                coords = data["routes"][0]["geometry"]["coordinates"]
                if len(coords) >= 2:
                    wkt_pts = ", ".join(f"{pt[0]} {pt[1]}" for pt in coords)
                    return WKTElement(f"LINESTRING({wkt_pts})", srid=4326)
    except Exception as e:
        print(f"OSRM route lookup error: {e}. Falling back to 2-point LINESTRING.")

    return WKTElement(f"LINESTRING({start_lon} {start_lat}, {end_lon} {end_lat})", srid=4326)


router = APIRouter(
    prefix="/roads",
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
    response_model=RoadResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
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

    route_geometry = None
    if (
        road.start_latitude is not None
        and road.start_longitude is not None
        and road.end_latitude is not None
        and road.end_longitude is not None
    ):
        route_geometry = fetch_osrm_linestring(
            road.start_longitude,
            road.start_latitude,
            road.end_longitude,
            road.end_latitude
        )

    new_road = Road(
        zone_id=road.zone_id,
        road_name=road.road_name,
        road_type=road.road_type,
        start_location=start_location,
        end_location=end_location,
        route_geometry=route_geometry,
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
    search: Optional[str] = Query(default=None, description="Optional road name fragment to search for in the real roads table"),
    db: Session = Depends(get_db)
):
    query = db.query(Road)
    if search is not None and search.strip():
        query = query.filter(Road.road_name.ilike(f"%{search.strip()}%"))
    roads = query.order_by(Road.road_name.asc()).all()
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
    response_model=RoadResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
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
    coords_changed = False
    if road.start_latitude is not None and road.start_longitude is not None:
        db_road.start_location = WKTElement(
            f"POINT({road.start_longitude} {road.start_latitude})",
            srid=4326
        )
        coords_changed = True
    if road.end_latitude is not None and road.end_longitude is not None:
        db_road.end_location = WKTElement(
            f"POINT({road.end_longitude} {road.end_latitude})",
            srid=4326
        )
        coords_changed = True

    if coords_changed and db_road.start_location and db_road.end_location:
        try:
            s_p = to_shape(db_road.start_location)
            e_p = to_shape(db_road.end_location)
            db_road.route_geometry = fetch_osrm_linestring(s_p.x, s_p.y, e_p.x, e_p.y)
        except Exception as e:
            print(f"Could not recompute route geometry on update: {e}")
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


@router.delete(
    "/{road_id}",
    dependencies=[Depends(require_roles("SUPER_ADMIN"))]
)
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