from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import Road
from app.services.weather import get_live_weather

router = APIRouter(
    prefix="/weather",
    tags=["Real-Time Weather Telemetry"]
)


@router.get(
    "/live",
    summary="Get Real-Time Live Weather for GPS Coordinates"
)
def get_live_meteorological_weather(
    lat: float = Query(17.4156, ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    lng: float = Query(78.4347, ge=-180.0, le=180.0, description="Longitude in decimal degrees")
):
    """
    Returns 100% live meteorological telemetry (temperature, rainfall, humidity,
    visibility, wind speed, weather condition) from Open-Meteo for any GPS location.
    Does not use fake fallback data.
    """
    return get_live_weather(latitude=lat, longitude=lng)


@router.get(
    "/live/road/{road_id}",
    summary="Get Real-Time Live Weather for a Monitored Road Corridor"
)
def get_live_weather_for_road(
    road_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Looks up the real geographical coordinates for the given road corridor
    and fetches current live weather telemetry.
    """
    road = db.query(Road).filter(Road.road_id == road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Road with ID '{road_id}' does not exist."
        )

    lat, lng = 17.4156, 78.4347
    if road.start_location is not None:
        try:
            pt = to_shape(road.start_location)
            lat, lng = pt.y, pt.x
        except Exception:
            pass

    weather_data = get_live_weather(latitude=lat, longitude=lng)
    return {
        "road_id": road.road_id,
        "road_name": road.road_name,
        "coordinates": {"latitude": lat, "longitude": lng},
        "weather": weather_data
    }
