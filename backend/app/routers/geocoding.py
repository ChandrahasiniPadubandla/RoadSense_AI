import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.geocoding import (
    GeocodeSearchResult,
    ReverseGeocodeResult,
    NearestRoadResult,
    DrivingRouteResult
)
from app.services.geocoding import (
    geocode_location,
    reverse_geocode,
    find_nearest_road_by_coordinates,
    get_driving_route
)

logger = logging.getLogger("Metrivon.geocoding_router")

router = APIRouter(
    prefix="/geo",
    tags=["Geocoding & Spatial Location"]
)


@router.get(
    "/search",
    response_model=List[GeocodeSearchResult],
    summary="Search Real Coordinates for Place / Landmark"
)
def search_location(
    query: str = Query(..., min_length=2, description="Place name, area, road, or landmark to search"),
    city: Optional[str] = Query("Hyderabad", description="City bias for prioritizing local search results"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Geocodes text queries into real GPS latitude & longitude.
    Integrates Metrivon AI monitored corridors, curated Hyderabad transit hubs,
    and Komoot Photon API (Elasticsearch + OSM) with local in-memory caching.
    """
    results = geocode_location(query=query, city_bias=city or "", limit=limit, db=db)
    return results


@router.get(
    "/reverse",
    response_model=ReverseGeocodeResult,
    summary="Reverse Geocode GPS Coordinates to Road/Area Name"
)
def reverse_geocode_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude of the location"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitude of the location")
):
    """
    Converts GPS latitude & longitude (from browser GPS or map click) into human-readable road,
    suburb, and city names using Photon reverse geocoding.
    """
    data = reverse_geocode(latitude=lat, longitude=lng)
    if not data:
        raise HTTPException(status_code=404, detail="Location could not be reverse-geocoded")
    return data


@router.get(
    "/nearest-road",
    response_model=NearestRoadResult,
    summary="Snap GPS Point to Nearest Monitored Road Corridor via PostGIS"
)
def get_nearest_road(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    db: Session = Depends(get_db)
):
    """
    Uses PostGIS spatial indexing to find the closest monitored road corridor
    in the database to the given GPS coordinates.
    """
    road = find_nearest_road_by_coordinates(db=db, latitude=lat, longitude=lng)
    if not road:
        raise HTTPException(status_code=404, detail="No registered road found near given coordinates")

    return NearestRoadResult(
        road_id=road.road_id,
        road_name=road.road_name,
        road_type=road.road_type,
        speed_limit=float(road.speed_limit) if road.speed_limit else None,
        road_capacity=road.road_capacity,
        number_of_lanes=road.number_of_lanes,
        road_condition=road.road_condition
    )


@router.get(
    "/route",
    response_model=DrivingRouteResult,
    summary="Get Street-Level Route Geometry by Vehicle Mode (Car, Bike, Walk)"
)
def get_route(
    start_lat: float = Query(..., ge=-90.0, le=90.0, description="Start Latitude"),
    start_lng: float = Query(..., ge=-180.0, le=180.0, description="Start Longitude"),
    end_lat: float = Query(..., ge=-90.0, le=90.0, description="End Latitude"),
    end_lng: float = Query(..., ge=-180.0, le=180.0, description="End Longitude"),
    mode: str = Query("driving", description="Vehicle routing mode: 'driving' (car), 'bike', or 'foot' (walk)")
):
    """
    Returns actual street route coordinates [[lat, lng], ...], distance in km,
    turn-by-turn directions, and travel duration tailored to the vehicle profile (driving, bike, foot).
    """
    route_info = get_driving_route(
        start_lat=start_lat,
        start_lng=start_lng,
        end_lat=end_lat,
        end_lng=end_lng,
        mode=mode
    )
    return DrivingRouteResult(**route_info)

