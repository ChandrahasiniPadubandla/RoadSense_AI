from typing import Optional, List
from fastapi import APIRouter, Query, Depends
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.database.connection import get_db
from app.database.models import AccidentHotspot, TrafficZone
from app.schemas.ml import HotspotRequest, HotspotResponse, HotspotItem
from app.services.hotspot_service import (
    sync_empirical_hotspots,
    resolve_risk_level,
    find_hotspot_for_route,
    resolve_hotspot_zone,
)


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

    results = []
    for hotspot, zone in rows:
        zone = zone or resolve_hotspot_zone(db, hotspot)
        lat, lon = _read_point(hotspot.location if hotspot.location is not None else (zone.location if zone else None))
        score = float(hotspot.risk_score) if hotspot.risk_score is not None else None
        level = resolve_risk_level(score) if score is not None else (hotspot.risk_level or "LOW")
        zone_id = str(hotspot.zone_id) if hotspot.zone_id else None
        zone_name = (zone.zone_name or "").strip() if zone else ""
        results.append({
            "hotspot_id": str(hotspot.hotspot_id),
            "zone_id": zone_id,
            "zone_name": zone_name or None,
            "zone_label": (
                zone_name
                or (f"Zone {zone_id}" if zone_id else None)
                or "Unassigned zone"
            ),
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
    force_predict: bool = Query(False, description="Force real-time ML model re-prediction"),
    hour: Optional[int] = Query(None, ge=0, le=23, description="Specific hour of day (0-23) for dynamic prediction"),
    weather: Optional[str] = Query(None, description="Weather condition, e.g. 'Clear', 'Rain'"),
    db: Session = Depends(get_db),
):
    """
    Directly evaluates whether the given start and end locations form an accident hotspot corridor.
    Supports real-time re-prediction with dynamic hour and weather conditions.
    """
    found = find_hotspot_for_route(
        db=db,
        start_location=start_location,
        end_location=end_location,
        start_lat=start_latitude,
        start_lng=start_longitude,
        end_lat=end_latitude,
        end_lng=end_longitude,
        force_predict=force_predict,
        hour=hour,
        weather=weather,
    )
    if found:
        acc_cnt = int(found.get("accident_count") or 0)
        risk_lvl = found.get("risk_level") or "LOW"
        is_hotspot = found.get("is_hotspot") if "is_hotspot" in found else (acc_cnt >= 15 or risk_lvl in ["HIGH", "SEVERE", "CRITICAL"])
        score = found.get("risk_score")
        s_name = found.get("start_location") or start_location
        e_name = found.get("end_location") or end_location
        source = found.get("source") or "ml_model_prediction"
        prob = found.get("hotspot_probability")
        dist = found.get("distance_km")

        dist_str = f" ({dist} km)" if dist else ""
        prob_str = f" ({prob:.1f}% hotspot probability)" if prob is not None else ""
        hist_str = f" Corridor has {acc_cnt} recorded historical accidents." if acc_cnt > 0 else " (New corridor, 0 past recorded crashes)."

        if is_hotspot:
            msg = f"AI / ML Model Prediction: Route corridor {s_name} -> {e_name}{dist_str} is classified as an accident hotspot{prob_str} with {score:.1f}% predicted risk ({risk_lvl}).{hist_str}"
        else:
            prob_sub = f", Hotspot Probability: {prob:.1f}%" if prob is not None else ""
            msg = f"AI / ML Model Prediction: Route corridor {s_name} -> {e_name}{dist_str} is normal / low risk (Predicted Risk: {score:.1f}% - {risk_lvl}{prob_sub}). Corridor does not meet accident hotspot thresholds.{hist_str}"

        return {
            "is_hotspot": is_hotspot,
            "found": True,
            "hotspot_id": found.get("hotspot_id"),
            "start_location": s_name,
            "end_location": e_name,
            "accident_count": acc_cnt,
            "risk_score": score,
            "risk_level": risk_lvl,
            "hotspot_probability": prob,
            "distance_km": dist,
            "source": source,
            "contributing_factors": found.get("contributing_factors") or [],
            "latitude": found.get("latitude"),
            "longitude": found.get("longitude"),
            "message": msg,
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
    Computes top accident hotspots from database records,
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
            zone_id = found.get("zone_id")
            zone_label = (
                found.get("zone_name")
                or (f"Zone {zone_id}" if zone_id else None)
                or f"{found.get('start_location')} -> {found.get('end_location')}"
            )
            item = HotspotItem(
                road_id="N/A",
                zone_id=zone_id,
                location=zone_label,
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
        if zone:
            zone_name = (zone.zone_name or "").strip()
            loc_label = zone_name or f"Zone {h.zone_id}"
        elif h.zone_id:
            loc_label = f"Zone {h.zone_id}"
        elif h.start_location and h.end_location:
            loc_label = f"{h.start_location} -> {h.end_location}"
        else:
            loc_label = "Unassigned zone"

        score = float(h.risk_score) if h.risk_score is not None else None
        items.append(
            HotspotItem(
                road_id=str(h.zone_id) if h.zone_id else "N/A",
                zone_id=str(h.zone_id) if h.zone_id else None,
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
