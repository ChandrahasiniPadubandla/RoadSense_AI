from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    Accident,
    AccidentHotspot
)


router = APIRouter(
    prefix="/api/map",
    tags=["Map Visualization"]
)


def _get_congestion_color(level: Optional[str], density: Optional[float]) -> str:
    """
    Returns standard hex color code based on congestion level or density:
    - Green: Low traffic (#10B981)
    - Yellow: Moderate traffic (#F59E0B)
    - Orange: High traffic (#F97316)
    - Red: Severe traffic (#EF4444)
    """
    if level:
        lvl = level.strip().upper()
        if lvl == "SEVERE":
            return "#EF4444"
        elif lvl == "HIGH":
            return "#F97316"
        elif lvl in ["MEDIUM", "MODERATE"]:
            return "#F59E0B"
        elif lvl == "LOW":
            return "#10B981"

    if density is not None:
        if density >= 85:
            return "#EF4444"
        elif density >= 70:
            return "#F97316"
        elif density >= 40:
            return "#F59E0B"
        else:
            return "#10B981"

    return "#9CA3AF"  # Default gray for no live data


def _get_accident_marker_color(severity: Optional[str]) -> str:
    if severity:
        sev = severity.strip().upper()
        if sev == "FATAL":
            return "#7F1D1D"  # Deep red/maroon
        elif sev == "SEVERE":
            return "#DC2626"  # Red
        elif sev in ["MODERATE", "MEDIUM"]:
            return "#F59E0B"  # Amber
        elif sev == "MINOR":
            return "#2563EB"  # Blue
    return "#DC2626"


@router.get(
    "/traffic-layer",
    summary="Get GeoJSON Traffic Layer for Leaflet Map"
)
def get_traffic_layer(
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Returns a GeoJSON FeatureCollection containing road line segments styled
    by current live traffic congestion conditions (Green, Yellow, Orange, Red)
    for direct integration with Leaflet (`L.geoJSON(...)`) or MapLibre.
    """
    # 1. Fetch active roads that have geographic coordinates
    roads = (
        db.query(Road)
        .filter(
            Road.is_active == True,
            Road.start_location.isnot(None),
            Road.end_location.isnot(None)
        )
        .all()
    )

    # 2. Get latest traffic record for each road
    latest_traffic_sub = (
        db.query(
            TrafficRecord.road_id,
            func.max(TrafficRecord.timestamp).label("max_ts")
        )
        .group_by(TrafficRecord.road_id)
        .subquery()
    )

    latest_records = (
        db.query(TrafficRecord)
        .join(
            latest_traffic_sub,
            and_(
                TrafficRecord.road_id == latest_traffic_sub.c.road_id,
                TrafficRecord.timestamp == latest_traffic_sub.c.max_ts
            )
        )
        .all()
    )

    traffic_by_road: dict[UUID, TrafficRecord] = {
        r.road_id: r for r in latest_records
    }

    features = []
    for road in roads:
        try:
            start_p = to_shape(road.start_location)
            end_p = to_shape(road.end_location)
        except Exception:
            continue

        tr = traffic_by_road.get(road.road_id)
        congestion = tr.congestion_level if tr else None
        density = float(tr.traffic_density) if tr and tr.traffic_density is not None else None
        color = _get_congestion_color(congestion, density)

        capacity_utilization = None
        if tr and road.road_capacity and road.road_capacity > 0:
            capacity_utilization = round((tr.vehicle_count / road.road_capacity) * 100, 1)

        feature = {
            "type": "Feature",
            "id": str(road.road_id),
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [start_p.x, start_p.y],  # [longitude, latitude]
                    [end_p.x, end_p.y]
                ]
            },
            "properties": {
                "road_id": str(road.road_id),
                "road_name": road.road_name,
                "road_type": road.road_type,
                "speed_limit": float(road.speed_limit) if road.speed_limit else None,
                "road_capacity": road.road_capacity,
                "congestion_level": congestion or "UNKNOWN",
                "traffic_density": density,
                "average_speed": float(tr.average_speed) if tr and tr.average_speed is not None else None,
                "vehicle_count": tr.vehicle_count if tr else None,
                "capacity_utilization": capacity_utilization,
                "weather_condition": tr.weather_condition if tr else None,
                "color": color,
                "last_updated": tr.timestamp.isoformat() if tr else None
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get(
    "/accident-layer",
    summary="Get GeoJSON Accident Markers Layer for Leaflet Map"
)
def get_accident_layer(
    days: Optional[int] = Query(default=None, description="Filter accidents from last N days"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (MINOR, MODERATE, SEVERE, FATAL)"),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Returns a GeoJSON FeatureCollection of accident incident points with
    severity markers, injury details, and timestamps for Leaflet map display.
    """
    query = (
        db.query(Accident, Road.road_name)
        .outerjoin(Road, Accident.road_id == Road.road_id)
        .filter(Accident.location.isnot(None))
    )

    if days is not None and days > 0:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(Accident.accident_datetime >= cutoff)

    if severity:
        query = query.filter(Accident.severity.ilike(severity.strip()))

    accidents_with_roads = query.order_by(Accident.accident_datetime.desc()).all()

    features = []
    for accident, road_name in accidents_with_roads:
        try:
            pt = to_shape(accident.location)
        except Exception:
            continue

        color = _get_accident_marker_color(accident.severity)

        feature = {
            "type": "Feature",
            "id": str(accident.accident_id),
            "geometry": {
                "type": "Point",
                "coordinates": [pt.x, pt.y]  # [longitude, latitude]
            },
            "properties": {
                "accident_id": str(accident.accident_id),
                "road_id": str(accident.road_id),
                "road_name": road_name or "Unknown Road",
                "severity": accident.severity,
                "fatalities": accident.fatalities or 0,
                "injuries": accident.injuries or 0,
                "vehicle_count": accident.vehicle_count,
                "weather_condition": accident.weather_condition,
                "road_condition": accident.road_condition,
                "accident_time": accident.accident_datetime.isoformat() if accident.accident_datetime else None,
                "description": accident.description,
                "marker_color": color
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get(
    "/hotspots-layer",
    summary="Get GeoJSON Accident Hotspots / Hazard Zones"
)
def get_hotspots_layer(
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Returns GeoJSON Point features with risk scores and accident counts
    for rendering hazard zones or heatmap overlays on the map.
    """
    hotspots = db.query(AccidentHotspot).filter(AccidentHotspot.location.isnot(None)).all()

    features = []
    for h in hotspots:
        try:
            pt = to_shape(h.location)
        except Exception:
            continue

        risk_level = h.risk_level or "HIGH"
        feature = {
            "type": "Feature",
            "id": str(h.hotspot_id),
            "geometry": {
                "type": "Point",
                "coordinates": [pt.x, pt.y]
            },
            "properties": {
                "hotspot_id": str(h.hotspot_id),
                "zone_id": str(h.zone_id) if h.zone_id else None,
                "accident_count": h.accident_count,
                "risk_score": float(h.risk_score) if h.risk_score is not None else None,
                "risk_level": risk_level,
                "color": "#DC2626" if risk_level.upper() in ["HIGH", "CRITICAL"] else "#F59E0B"
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }
