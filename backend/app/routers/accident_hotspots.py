from fastapi import APIRouter, Query, Depends
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import AccidentHotspot, TrafficZone
from app.schemas.ml import HotspotRequest, HotspotResponse, HotspotItem
from app.services.hotspot_service import sync_empirical_hotspots, resolve_risk_level


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
        score = float(hotspot.risk_score) if hotspot.risk_score is not None else None
        level = resolve_risk_level(score) if score is not None else (hotspot.risk_level or "LOW")
        results.append({
            "hotspot_id": str(hotspot.hotspot_id),
            "zone_id": str(hotspot.zone_id) if hotspot.zone_id else None,
            "zone_name": zone.zone_name if zone else None,
            "accident_count": hotspot.accident_count,
            "risk_score": score,
            "risk_level": level,
            "latitude": lat,
            "longitude": lon,
            "calculated_at": hotspot.calculated_at.isoformat() if hotspot.calculated_at else None,
        })
    return results


@router.post(
    "/predict",
    response_model=HotspotResponse,
    summary="Identify and store accident hotspots in the database",
)
def predict_accident_hotspots(
    request: HotspotRequest,
    db: Session = Depends(get_db),
) -> HotspotResponse:
    """
    Computes top accident hotspots from empirical datasets / ML service,
    stores them into the `accident_hotspots` database table with their resolved
    geography point and traffic zones, and returns the persisted hotspot list.
    """
    persisted_hotspots = sync_empirical_hotspots(db=db, top_n=request.top_n)

    items = []
    for h in persisted_hotspots:
        lat, lon = _read_point(h.location)
        zone = db.query(TrafficZone).filter(TrafficZone.zone_id == h.zone_id).first() if h.zone_id else None
        items.append(
            HotspotItem(
                road_id=str(h.zone_id) if h.zone_id else "N/A",
                location=zone.zone_name if zone else "Monitored Zone",
                latitude=lat if lat is not None else 0.0,
                longitude=lon if lon is not None else 0.0,
                accident_count=h.accident_count or 0,
                risk_level=h.risk_level or "MEDIUM",
            )
        )

    return HotspotResponse(hotspots=items, model_status="database-persisted")
