from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Road, WeatherRecord
from app.schemas.weather import WeatherCreate, WeatherResponse, WeatherUpdate





router = APIRouter(
    prefix="/api/weather",
    tags=["Weather Management"]
)


def _get_road(road_id: UUID, db: Session) -> Road:
    road = db.query(Road).filter(Road.road_id == road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Road with ID '{road_id}' does not exist. Cannot link or query weather data."
        )
    return road


@router.post("", response_model=WeatherResponse)
def create_weather_record(
    weather: WeatherCreate,
    db: Session = Depends(get_db)
):
    _get_road(weather.road_id, db)
    record = WeatherRecord(**weather.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[WeatherResponse])
def get_weather_records(db: Session = Depends(get_db)):
    return (
        db.query(WeatherRecord)
        .order_by(WeatherRecord.timestamp.desc())
        .all()
    )


@router.get("/road/{road_id}", response_model=list[WeatherResponse])
def get_road_weather(road_id: UUID, db: Session = Depends(get_db)):
    _get_road(road_id, db)
    return (
        db.query(WeatherRecord)
        .filter(WeatherRecord.road_id == road_id)
        .order_by(WeatherRecord.timestamp.desc())
        .all()
    )


@router.get("/{weather_id}", response_model=WeatherResponse)
def get_weather_record(weather_id: UUID, db: Session = Depends(get_db)):
    record = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.weather_id == weather_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Weather record with ID '{weather_id}' does not exist."
        )
    return record


@router.put("/{weather_id}", response_model=WeatherResponse)
def update_weather_record(
    weather_id: UUID,
    weather: WeatherUpdate,
    db: Session = Depends(get_db)
):
    record = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.weather_id == weather_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update: Weather record with ID '{weather_id}' does not exist."
        )

    updates = weather.model_dump(exclude_unset=True)
    if "road_id" in updates:
        _get_road(updates["road_id"], db)
    for field, value in updates.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{weather_id}")
def delete_weather_record(weather_id: UUID, db: Session = Depends(get_db)):
    record = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.weather_id == weather_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot delete: Weather record with ID '{weather_id}' does not exist."
        )

    db.delete(record)
    db.commit()
    return {"message": "Weather record deleted successfully"}
