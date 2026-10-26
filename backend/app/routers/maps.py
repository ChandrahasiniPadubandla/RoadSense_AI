import time
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    TrafficPrediction,
    Accident,
    AccidentHotspot,
    TrafficAnomaly
)
from app.services.hotspot_service import resolve_risk_level

router = APIRouter(
    prefix="/map",
    tags=["Map Visualization"]
)

_TRAFFIC_LAYER_CACHE = {"ts": 0.0, "data": None}
_HOTSPOTS_LAYER_CACHE = {"ts": 0.0, "data": None}
_MAP_CACHE_TTL = 15.0  # 15 seconds


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
    now_ts = time.time()
    if _TRAFFIC_LAYER_CACHE["data"] is not None and (now_ts - _TRAFFIC_LAYER_CACHE["ts"]) < _MAP_CACHE_TTL:
        return _TRAFFIC_LAYER_CACHE["data"]

    # 1. Fetch active roads that have geometry or coordinates
    roads = (
        db.query(Road)
        .filter(
            Road.is_active.is_(True),
            or_(
                Road.route_geometry.isnot(None),
                and_(
                    Road.start_location.isnot(None),
                    Road.end_location.isnot(None)
                )
            )
        )
        .all()
    )

    # 2. Get latest AI traffic prediction for each road (primary source)
    latest_pred_sub = (
        db.query(
            TrafficPrediction.start_road_id.label("road_id"),
            func.max(TrafficPrediction.created_at).label("max_created")
        )
        .filter(TrafficPrediction.start_road_id.isnot(None))
        .group_by(TrafficPrediction.start_road_id)
        .subquery()
    )

    latest_predictions = (
        db.query(TrafficPrediction)
        .join(
            latest_pred_sub,
            and_(
                TrafficPrediction.start_road_id == latest_pred_sub.c.road_id,
                TrafficPrediction.created_at == latest_pred_sub.c.max_created
            )
        )
        .all()
    )

    pred_by_road: dict[UUID, TrafficPrediction] = {
        p.start_road_id: p for p in latest_predictions if p.start_road_id is not None
    }

    # 3. Get latest traffic telemetry record for each road (secondary telemetry source)
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
        line_coords = None
        if road.route_geometry is not None:
            try:
                shape = to_shape(road.route_geometry)
                line_coords = [[pt[0], pt[1]] for pt in shape.coords]
            except Exception:
                line_coords = None

        if not line_coords or len(line_coords) < 2:
            try:
                start_p = to_shape(road.start_location)
                end_p = to_shape(road.end_location)
                line_coords = [
                    [start_p.x, start_p.y],  # [longitude, latitude]
                    [end_p.x, end_p.y]
                ]
            except Exception:
                continue

        pred = pred_by_road.get(road.road_id)
        tr = traffic_by_road.get(road.road_id)

        # Prioritize AI Traffic Prediction over raw record; do NOT fake as LOW
        if pred and pred.predicted_congestion:
            congestion = pred.predicted_congestion.upper()
        elif tr and tr.congestion_level:
            congestion = tr.congestion_level.upper()
        else:
            congestion = None

        # Vehicle Count: Use predicted vehicle count, fallback to telemetry
        if pred and pred.predicted_vehicle_count is not None:
            vehicle_count = pred.predicted_vehicle_count
        elif tr and tr.vehicle_count is not None:
            vehicle_count = tr.vehicle_count
        else:
            vehicle_count = None

        # Average Speed
        if tr and tr.average_speed is not None and float(tr.average_speed) > 0:
            avg_speed = float(tr.average_speed)
        elif road.speed_limit is not None:
            avg_speed = float(road.speed_limit)
        else:
            avg_speed = 50.0

        density = float(tr.traffic_density) if tr and tr.traffic_density is not None else None
        color = _get_congestion_color(congestion, density)

        capacity_utilization = None
        if road.road_capacity and road.road_capacity > 0 and vehicle_count is not None:
            capacity_utilization = round((vehicle_count / road.road_capacity) * 100, 1)

        confidence = float(pred.confidence_score) if pred and pred.confidence_score is not None else None
        last_updated_dt = (pred.created_at if pred else (tr.timestamp if tr else None))

        road_id_str = str(road.road_id)

        feature = {
            "type": "Feature",
            "id": road_id_str,
            "geometry": {
                "type": "LineString",
                "coordinates": line_coords
            },
            "properties": {
                "road_id": str(road.road_id),
                "road_name": road.road_name,
                "road_type": road.road_type,
                "speed_limit": float(road.speed_limit) if road.speed_limit else None,
                "road_capacity": road.road_capacity,
                "congestion_level": congestion,
                "confidence_score": confidence,
                "traffic_density": density,
                "average_speed": avg_speed,
                "vehicle_count": vehicle_count,
                "capacity_utilization": capacity_utilization,
                "weather_condition": (tr.weather_condition if tr else None) or "Clear",
                "color": color,
                "is_predicted": pred is not None,
                "last_updated": last_updated_dt.isoformat() if last_updated_dt else None
            }
        }
        features.append(feature)

    res = {
        "type": "FeatureCollection",
        "features": features
    }
    _TRAFFIC_LAYER_CACHE["ts"] = now_ts
    _TRAFFIC_LAYER_CACHE["data"] = res
    return res


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
    now_ts = time.time()
    if _HOTSPOTS_LAYER_CACHE["data"] is not None and (now_ts - _HOTSPOTS_LAYER_CACHE["ts"]) < _MAP_CACHE_TTL:
        return _HOTSPOTS_LAYER_CACHE["data"]

    hotspots = db.query(AccidentHotspot).filter(AccidentHotspot.location.isnot(None)).all()

    features = []
    for h in hotspots:
        try:
            pt = to_shape(h.location)
        except Exception:
            continue

        score = float(h.risk_score) if h.risk_score is not None else None
        risk_level = resolve_risk_level(score) if score is not None else (h.risk_level or "HIGH")
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
                "risk_score": score,
                "risk_level": risk_level,
                "color": "#DC2626" if risk_level.upper() in ["HIGH", "SEVERE", "CRITICAL"] else "#F59E0B"
            }
        }
        features.append(feature)

    res = {
        "type": "FeatureCollection",
        "features": features
    }
    _HOTSPOTS_LAYER_CACHE["ts"] = now_ts
    _HOTSPOTS_LAYER_CACHE["data"] = res
    return res


@router.get(
    "/anomalies-layer",
    summary="Get GeoJSON Traffic Anomaly Layer for Leaflet Map"
)
def get_anomalies_layer(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Returns a GeoJSON FeatureCollection of detected traffic anomalies
    (unusual vehicle-count spikes/drops flagged by the Isolation Forest
    model), positioned at their road's location, for map display.
    """
    rows = (
        db.query(TrafficAnomaly, Road)
        .join(Road, TrafficAnomaly.road_id == Road.road_id)
        .filter(Road.start_location.isnot(None))
        .order_by(TrafficAnomaly.detected_at.desc())
        .limit(limit)
        .all()
    )

    features = []
    for anomaly, road in rows:
        try:
            pt = to_shape(road.start_location)
        except Exception:
            continue

        score = float(anomaly.anomaly_score) if anomaly.anomaly_score is not None else None
        severity = "HIGH" if score is not None and score >= 70 else "MEDIUM"

        feature = {
            "type": "Feature",
            "id": str(anomaly.anomaly_id),
            "geometry": {
                "type": "Point",
                "coordinates": [pt.x, pt.y]
            },
            "properties": {
                "anomaly_id": str(anomaly.anomaly_id),
                "road_id": str(anomaly.road_id),
                "road_name": road.road_name,
                "anomaly_type": anomaly.anomaly_type,
                "anomaly_score": score,
                "severity": severity,
                "normal_vehicle_count": anomaly.normal_vehicle_count,
                "actual_vehicle_count": anomaly.actual_vehicle_count,
                "description": anomaly.description,
                "status": anomaly.status,
                "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None,
                "color": "#A855F7" if severity == "HIGH" else "#D8B4FE"
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }
