from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import WeatherRecord
from app.schemas.weather import WeatherResponse


router = APIRouter(
    prefix="/api/weather",
    tags=["Weather Records"]
)


def _format_weather(w: WeatherRecord) -> WeatherResponse:
    return WeatherResponse(
        weather_id=w.weather_id,
        road_id=w.road_id,
        timestamp=w.timestamp,
        temperature=float(w.temperature) if w.temperature is not None else None,
        rainfall=float(w.rainfall) if w.rainfall is not None else None,
        humidity=float(w.humidity) if w.humidity is not None else None,
        visibility=float(w.visibility) if w.visibility is not None else None,
        wind_speed=float(w.wind_speed) if w.wind_speed is not None else None,
        weather_condition=w.weather_condition
    )


@router.get("", response_model=list[WeatherResponse], summary="Get weather observations")
def get_weather_records(
    road_id: Optional[UUID] = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    query = db.query(WeatherRecord)
    if road_id:
        query = query.filter(WeatherRecord.road_id == road_id)

    records = query.order_by(WeatherRecord.timestamp.desc()).limit(limit).all()
    return [_format_weather(r) for r in records]
