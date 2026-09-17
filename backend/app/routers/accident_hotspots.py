from typing import Optional

from fastapi import APIRouter, Query
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database.connection import get_db
from app.database.models import AccidentHotspot, TrafficZone
from app.schemas.ml import HotspotRequest, HotspotResponse
from app.services.ml_service import ml_service


router = APIRouter(
    prefix="/hotspots",
    tags=["Accident Hotspot Analysis"],
)


def _read_point(geo_value):
    if geo_value is None:
        return None, None
    try:
        point = to_shape(geo_value)
        return float(point.y), float(point.x)
    except Exception:
        return None, None


@router.get(
    "",
    summary="List real accident hotspots calculated from the database (accident_hotspots table)",
)
def list_accident_hotspots(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns REAL hotspot rows from the `accident_hotspots` table, joined with
    their traffic zone name/location. This is the same data source used by
    the chatbot's `get_accident_hotspots` tool, so the Hotspots page and the
    chatbot always agree.

    Returns an empty list (not fabricated data) if hotspot detection has not
    been run yet / no rows exist.
    """
    rows = (
        db.query(AccidentHotspot, TrafficZone)
        .outerjoin(TrafficZone, TrafficZone.zone_id == AccidentHotspot.zone_id)
        .order_by(AccidentHotspot.accident_count.desc())
        .limit(limit)
        .all()
    )

    results = []
    for hotspot, zone in rows:
        lat, lon = _read_point(hotspot.location if hotspot.location is not None else (zone.location if zone else None))
        results.append({
            "hotspot_id": str(hotspot.hotspot_id),
            "zone_id": str(hotspot.zone_id) if hotspot.zone_id else None,
            "zone_name": zone.zone_name if zone else None,
            "accident_count": hotspot.accident_count,
            "risk_score": float(hotspot.risk_score) if hotspot.risk_score is not None else None,
            "risk_level": hotspot.risk_level,
            "latitude": lat,
            "longitude": lon,
            "calculated_at": hotspot.calculated_at.isoformat() if hotspot.calculated_at else None,
        })
    return results


@router.post(
    "/predict",
    response_model=HotspotResponse,
    summary="[Legacy] Identify hotspots from a static CSV dataset — superseded by GET /hotspots",
    deprecated=True,
)
def predict_accident_hotspots(
    request: HotspotRequest,
) -> HotspotResponse:
    """
    Kept for backward compatibility only. This computes hotspots from the
    OLD `ML/dataset/traffic_accident_balanced_10000.csv` file rather than the
    live `accident_hotspots` database table, so its numbers will not match
    the rest of the application (which is entirely database-driven). New
    integrations should use GET /hotspots instead.
    """
    return ml_service.get_accident_hotspots(request)
