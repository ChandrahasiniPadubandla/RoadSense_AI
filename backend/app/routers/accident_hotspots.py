from typing import Optional, List
from fastapi import APIRouter, Query, Depends
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.database.connection import get_db
from app.database.models import AccidentHotspot, TrafficZone
from app.schemas.ml import HotspotRequest, HotspotResponse, HotspotItem
from app.services.hotspot_service import sync_empirical_hotspots, resolve_risk_level, find_hotspot_for_route


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
    start_location: Optional[str] = Query(None, description="Filter hotspots by start location"),
    end_location: Optional[str] = Query(None, description="Filter hotspots by end location"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Returns REAL hotspot rows from the `accident_hotspots` table.
    Supports filtering by route corridor (start_location and/or end_location).
    Joined with traffic zone details.
    """
    query = (
        db.query(AccidentHotspot, TrafficZone)
        .outerjoin(TrafficZone, TrafficZone.zone_id == AccidentHotspot.zone_id)
    )

    clean_s = (start_location or "").strip().lower()
    clean_e = (end_location or "").strip().lower()

    if clean_s and clean_e:
        query = query.filter(
            or_(
                and_(
                    func.lower(AccidentHotspot.start_location).ilike(f"%{clean_s}%"),
                    func.lower(AccidentHotspot.end_location).ilike(f"%{clean_e}%"),
                ),
                and_(
                    func.lower(AccidentHotspot.start_location).ilike(f"%{clean_e}%"),
                    func.lower(AccidentHotspot.end_location).ilike(f"%{clean_s}%"),
                )
            )
        )
    elif clean_s:
        query = query.filter(
            or_(
                func.lower(AccidentHotspot.start_location).ilike(f"%{clean_s}%"),
                func.lower(AccidentHotspot.end_location).ilike(f"%{clean_s}%"),
                func.lower(TrafficZone.zone_name).ilike(f"%{clean_s}%"),
            )
        )
    elif clean_e:
        query = query.filter(
            or_(
                func.lower(AccidentHotspot.start_location).ilike(f"%{clean_e}%"),
                func.lower(AccidentHotspot.end_location).ilike(f"%{clean_e}%"),
                func.lower(TrafficZone.zone_name).ilike(f"%{clean_e}%"),
            )
        )

    rows = query.order_by(AccidentHotspot.accident_count.desc(), AccidentHotspot.risk_score.desc()).limit(limit).all()

    # If database has no route hotspots yet and start/end locations are provided, seed / find them
    if not rows and clean_s and clean_e:
        found = find_hotspot_for_route(db=db, start_location=start_location, end_location=end_location)
        if found:
            return [{
                "hotspot_id": found.get("hotspot_id"),
                "zone_id": None,
                "zone_name": None,
                "start_location": found.get("start_location"),
                "end_location": found.get("end_location"),
                "start_latitude": None,
                "start_longitude": None,
                "end_latitude": None,
                "end_longitude": None,
                "accident_count": found.get("accident_count"),
                "risk_score": found.get("risk_score"),
                "risk_level": found.get("risk_level"),
                "latitude": found.get("latitude"),
                "longitude": found.get("longitude"),
                "calculated_at": None,
            }]

    results = []
    for hotspot, zone in rows:
        lat, lon = _read_point(hotspot.location if hotspot.location is not None else (zone.location if zone else None))
        score = float(hotspot.risk_score) if hotspot.risk_score is not None else None
        level = resolve_risk_level(score) if score is not None else (hotspot.risk_level or "LOW")
        results.append({
            "hotspot_id": str(hotspot.hotspot_id),
            "zone_id": str(hotspot.zone_id) if hotspot.zone_id else None,
            "zone_name": zone.zone_name if zone else None,
            "start_location": hotspot.start_location,
            "end_location": hotspot.end_location,
            "start_latitude": float(hotspot.start_latitude) if hotspot.start_latitude is not None else None,
            "start_longitude": float(hotspot.start_longitude) if hotspot.start_longitude is not None else None,
            "end_latitude": float(hotspot.end_latitude) if hotspot.end_latitude is not None else None,
            "end_longitude": float(hotspot.end_longitude) if hotspot.end_longitude is not None else None,
            "accident_count": hotspot.accident_count or 0,
            "risk_score": score,
            "risk_level": level,
            "latitude": lat,
            "longitude": lon,
            "calculated_at": hotspot.calculated_at.isoformat() if hotspot.calculated_at else None,
        })
    return results


@router.get(
    "/check",
    summary="Check if a specific route (start and end location) is an accident hotspot",
)
def check_route_hotspot(
    start_location: str = Query(..., description="Start location name, e.g. 'Jubilee Hills'"),
    end_location: str = Query(..., description="End location name, e.g. 'Bachupally'"),
    start_latitude: Optional[float] = Query(None, description="Optional start latitude"),
    start_longitude: Optional[float] = Query(None, description="Optional start longitude"),
    end_latitude: Optional[float] = Query(None, description="Optional end latitude"),
    end_longitude: Optional[float] = Query(None, description="Optional end longitude"),
    db: Session = Depends(get_db),
):
    """
    Directly evaluates whether the given start and end locations form an accident hotspot corridor.
    """
    found = find_hotspot_for_route(
        db=db,
        start_location=start_location,
        end_location=end_location,
        start_lat=start_latitude,
        start_lng=start_longitude,
        end_lat=end_latitude,
        end_lng=end_longitude,
    )
    if found:
        acc_cnt = int(found.get("accident_count") or 0)
        risk_lvl = found.get("risk_level") or "LOW"
        is_hotspot = acc_cnt >= 15 or risk_lvl in ["HIGH", "SEVERE", "CRITICAL"]
        return {
            "is_hotspot": is_hotspot,
            "found": True,
            "hotspot_id": found.get("hotspot_id"),
            "start_location": found.get("start_location"),
            "end_location": found.get("end_location"),
            "accident_count": acc_cnt,
            "risk_score": found.get("risk_score"),
            "risk_level": risk_lvl,
            "latitude": found.get("latitude"),
            "longitude": found.get("longitude"),
            "message": f"Route corridor {found.get('start_location')} -> {found.get('end_location')} is an accident hotspot ({acc_cnt} accidents, {risk_lvl})."
        }
    return {
        "is_hotspot": False,
        "found": False,
        "hotspot_id": None,
        "start_location": start_location,
        "end_location": end_location,
        "accident_count": 0,
        "risk_score": 0.0,
        "risk_level": "LOW",
        "latitude": None,
        "longitude": None,
        "message": f"Route corridor {start_location} -> {end_location} does not currently meet accident hotspot thresholds."
    }


@router.post(
    "/predict",
    response_model=HotspotResponse,
    summary="Identify and store accident hotspots in the database, with support for route locations",
)
def predict_accident_hotspots(
    request: HotspotRequest,
    db: Session = Depends(get_db),
) -> HotspotResponse:
    """
    Computes top accident hotspots from database and dataset records,
    stores them into the `accident_hotspots` database table with their resolved
    start/end locations, geography points, and traffic zones.
    If start_location and end_location are passed in the request, evaluates
    and returns that specific route corridor.
    """
    # If specific route corridor was provided in request
    if request.start_location and request.end_location:
        found = find_hotspot_for_route(
            db=db,
            start_location=request.start_location,
            end_location=request.end_location,
            start_lat=request.start_latitude,
            start_lng=request.start_longitude,
            end_lat=request.end_latitude,
            end_lng=request.end_longitude,
        )
        if found:
            s_lat = request.start_latitude
            s_lng = request.start_longitude
            e_lat = request.end_latitude
            e_lng = request.end_longitude
            item = HotspotItem(
                road_id="N/A",
                location=f"{found.get('start_location')} -> {found.get('end_location')}",
                start_location=found.get("start_location"),
                end_location=found.get("end_location"),
                start_latitude=s_lat,
                start_longitude=s_lng,
                end_latitude=e_lat,
                end_longitude=e_lng,
                latitude=found.get("latitude") or 0.0,
                longitude=found.get("longitude") or 0.0,
                accident_count=int(found.get("accident_count") or 0),
                risk_level=found.get("risk_level") or "LOW",
                risk_score=found.get("risk_score"),
                average_risk=found.get("risk_score"),
                hotspot_id=str(found.get("hotspot_id")),
            )
            return HotspotResponse(hotspots=[item], model_status="corridor-matched")

    persisted_hotspots = sync_empirical_hotspots(db=db, top_n=request.top_n)

    zone_ids = [h.zone_id for h in persisted_hotspots if h.zone_id]
    zones_by_id = {
        z.zone_id: z for z in db.query(TrafficZone).filter(TrafficZone.zone_id.in_(zone_ids)).all()
    } if zone_ids else {}

    items = []
    for h in persisted_hotspots:
        lat, lon = _read_point(h.location)
        zone = zones_by_id.get(h.zone_id)
        if h.start_location and h.end_location:
            loc_label = f"{h.start_location} -> {h.end_location}"
        elif zone:
            loc_label = zone.zone_name
        else:
            loc_label = "Monitored Zone"

        score = float(h.risk_score) if h.risk_score is not None else None
        items.append(
            HotspotItem(
                road_id=str(h.zone_id) if h.zone_id else "N/A",
                location=loc_label,
                start_location=h.start_location,
                end_location=h.end_location,
                start_latitude=float(h.start_latitude) if h.start_latitude is not None else None,
                start_longitude=float(h.start_longitude) if h.start_longitude is not None else None,
                end_latitude=float(h.end_latitude) if h.end_latitude is not None else None,
                end_longitude=float(h.end_longitude) if h.end_longitude is not None else None,
                latitude=lat if lat is not None else 0.0,
                longitude=lon if lon is not None else 0.0,
                accident_count=h.accident_count or 0,
                risk_level=h.risk_level or "MEDIUM",
                risk_score=score,
                average_risk=score,
                hotspot_id=str(h.hotspot_id),
            )
        )

    return HotspotResponse(hotspots=items, model_status="database-persisted")
