import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.database.models import AccidentHotspot, TrafficZone, Road, Accident, AccidentPrediction

logger = logging.getLogger("Metrivon")

CSV_HOTSPOT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "predict_accident_risk",
        "accident_hotspots.csv"
    )
)


def resolve_risk_level(risk_score: float) -> str:
    """
    Determines categorical risk level strictly and consistently from risk score,
    matching project standards:
      - score >= 75.0: SEVERE
      - score >= 55.0: HIGH
      - score >= 30.0: MEDIUM
      - score < 30.0:  LOW
    """
    score = float(risk_score or 0.0)
    if score >= 75.0:
        return "SEVERE"
    elif score >= 55.0:
        return "HIGH"
    elif score >= 30.0:
        return "MEDIUM"
    return "LOW"


def _read_point(geo_value):
    if geo_value is None:
        return None, None
    try:
        point = to_shape(geo_value)
        return float(point.y), float(point.x)
    except Exception:
        return None, None


def upsert_accident_hotspot(
    db: Session,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    risk_level: Optional[str] = None,
    risk_score: float = 0.0,
    accident_count: int = 0,
    zone_id: Optional[UUID] = None,
    calculated_at: Optional[datetime] = None,
    existing: Optional[AccidentHotspot] = None,
    start_location: Optional[str] = None,
    end_location: Optional[str] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    end_latitude: Optional[float] = None,
    end_longitude: Optional[float] = None,
) -> AccidentHotspot:
    """
    Inserts or updates an accident hotspot in the `accident_hotspots` table.
    Supports both route corridor hotspots (start_location -> end_location) and zone hotspots.
    """
    now = calculated_at or datetime.utcnow()
    safe_risk_level = resolve_risk_level(risk_score)

    # Derive midpoint coordinate if start and end coordinates are provided
    if (latitude is None or longitude is None) and start_latitude is not None and end_latitude is not None:
        latitude = (float(start_latitude) + float(end_latitude)) / 2.0
        longitude = (float(start_longitude) + float(end_longitude)) / 2.0

    # If coordinates are still not provided, resolve strictly from the associated TrafficZone in DB
    if (latitude is None or longitude is None) and zone_id:
        zone = db.query(TrafficZone).filter(TrafficZone.zone_id == zone_id).first()
        if zone and zone.location is not None:
            lat, lng = _read_point(zone.location)
            if lat is not None and lng is not None:
                latitude, longitude = lat, lng

    loc_point = None
    if latitude is not None and longitude is not None:
        loc_point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

    # 1. Match existing hotspot by start and end locations if provided
    if existing is None and start_location and end_location:
        clean_s = start_location.strip().lower()
        clean_e = end_location.strip().lower()
        existing = (
            db.query(AccidentHotspot)
            .filter(
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
            .first()
        )

    # 2. Match existing hotspot by zone_id
    if existing is None and zone_id:
        existing = (
            db.query(AccidentHotspot)
            .filter(AccidentHotspot.zone_id == zone_id)
            .first()
        )

    # 3. Match by proximity to known real coordinates
    if not existing and latitude is not None and longitude is not None:
        nearby_hotspots = db.query(AccidentHotspot).all()
        for h in nearby_hotspots:
            if h.location is not None:
                h_lat, h_lng = _read_point(h.location)
                if h_lat is not None and h_lng is not None:
                    if abs(h_lat - latitude) < 0.008 and abs(h_lng - longitude) < 0.008:
                        existing = h
                        break

    if existing:
        existing.accident_count = max(existing.accident_count or 0, accident_count)
        existing.risk_score = round(max(float(existing.risk_score or 0.0), float(risk_score)), 2)
        existing.risk_level = resolve_risk_level(existing.risk_score)
        if loc_point is not None:
            existing.location = loc_point
        existing.calculated_at = now
        if zone_id and not existing.zone_id:
            existing.zone_id = zone_id
        if start_location and not existing.start_location:
            existing.start_location = start_location
        if end_location and not existing.end_location:
            existing.end_location = end_location
        if start_latitude is not None and not existing.start_latitude:
            existing.start_latitude = start_latitude
        if start_longitude is not None and not existing.start_longitude:
            existing.start_longitude = start_longitude
        if end_latitude is not None and not existing.end_latitude:
            existing.end_latitude = end_latitude
        if end_longitude is not None and not existing.end_longitude:
            existing.end_longitude = end_longitude
        return existing
    else:
        new_hotspot = AccidentHotspot(
            zone_id=zone_id,
            location=loc_point,
            start_location=start_location,
            end_location=end_location,
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            end_latitude=end_latitude,
            end_longitude=end_longitude,
            accident_count=accident_count,
            risk_score=round(float(risk_score), 2),
            risk_level=safe_risk_level,
            calculated_at=now,
        )
        db.add(new_hotspot)
        return new_hotspot


def find_hotspot_for_route(
    db: Session,
    start_location: str,
    end_location: str,
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
    end_lat: Optional[float] = None,
    end_lng: Optional[float] = None,
    zone_id: Optional[int] = None,
    force_predict: bool = False,
    hour: Optional[int] = None,
    weather: Optional[str] = None,
    traffic_density: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether the specified route corridor matches a known accident hotspot.
    ALWAYS performs dynamic ML model prediction for ANY corridor (whether it exists in historical data or not),
    and enriches the result with historical crash counts if present in the database or CSV.
    """
    clean_s = (start_location or "").strip().lower()
    clean_e = (end_location or "").strip().lower()

    if clean_s and clean_e:
        try:
            import sys
            _parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            if _parent not in sys.path:
                sys.path.insert(0, _parent)
            from predict_accident_risk.accident_hotspot_detection import detect_hotspot
            ml_pred = detect_hotspot(
                start_location=start_location,
                end_location=end_location,
                start_latitude=start_lat,
                start_longitude=start_lng,
                end_latitude=end_lat,
                end_longitude=end_lng,
                hour=hour,
                weather=weather,
                traffic_density=traffic_density,
                force_ml=force_predict,
            )
            if ml_pred and ml_pred.get("found"):
                # Check if also stored in DB
                db_match = (
                    db.query(AccidentHotspot)
                    .filter(
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
                    .first()
                )
                hotspot_id = str(db_match.hotspot_id) if db_match else None
                acc_cnt = ml_pred.get("historical_accidents") or (int(db_match.accident_count or 0) if db_match else 0)
                is_hs = ml_pred.get("is_hotspot", False)
                risk_sc = float(ml_pred.get("predicted_risk", 0.0))
                risk_lv = ml_pred.get("risk", "LOW")

                # If it's a hotspot and not yet in DB, persist it
                if is_hs and not db_match:
                    persisted = upsert_accident_hotspot(
                        db=db,
                        start_location=ml_pred.get("start_location"),
                        end_location=ml_pred.get("end_location"),
                        start_latitude=ml_pred.get("start_latitude"),
                        start_longitude=ml_pred.get("start_longitude"),
                        end_latitude=ml_pred.get("end_latitude"),
                        end_longitude=ml_pred.get("end_longitude"),
                        risk_level=risk_lv,
                        risk_score=risk_sc,
                        accident_count=acc_cnt if acc_cnt > 0 else 1,
                        zone_id=zone_id,
                    )
                    db.commit()
                    hotspot_id = str(persisted.hotspot_id)

                lat = ml_pred.get("start_latitude")
                lon = ml_pred.get("start_longitude")

                return {
                    "hotspot_id": hotspot_id,
                    "start_location": ml_pred.get("start_location") or start_location,
                    "end_location": ml_pred.get("end_location") or end_location,
                    "accident_count": acc_cnt,
                    "risk_score": risk_sc,
                    "risk_level": risk_lv,
                    "hotspot_probability": ml_pred.get("hotspot_probability"),
                    "distance_km": ml_pred.get("distance_km"),
                    "has_historical_data": ml_pred.get("has_historical_data", acc_cnt > 0),
                    "historical_accidents": acc_cnt,
                    "contributing_factors": ml_pred.get("contributing_factors") or [],
                    "is_hotspot": is_hs,
                    "source": "ml_model_prediction",
                    "latitude": lat,
                    "longitude": lon,
                }
        except Exception as exc:
            logger.warning("ML hotspot prediction failed: %s", exc)

    return None


def sync_empirical_hotspots(db: Session, top_n: int = 50) -> List[AccidentHotspot]:
    """
    Synchronizes accident hotspots into the PostgreSQL database.
    Integrates route-level hotspots (start_location -> end_location) from
    accident_hotspots.csv as well as real zone-level accident records.
    """
    persisted = []
    now = datetime.utcnow()

    # 1. First, sync route-level hotspots (from CSV if present, or in-memory from dataset)
    try:
        df = None
        if os.path.exists(CSV_HOTSPOT_PATH):
            try:
                import pandas as pd
                df = pd.read_csv(CSV_HOTSPOT_PATH)
            except Exception:
                df = None
        else:
            try:
                from predict_accident_risk.accident_hotspot_detection import detect_all_hotspots
                df = detect_all_hotspots(save_csv=False)
            except Exception:
                df = None

        if df is not None:
            for _, row in df.head(top_n).iterrows():
                s_name = str(row["start_location"])
                e_name = str(row["end_location"])
                s_lat = float(row["start_latitude"])
                s_lng = float(row["start_longitude"])
                e_lat = float(row["end_latitude"])
                e_lng = float(row["end_longitude"])
                acc_cnt = int(row["accidents"])
                avg_risk = float(row["average_risk"])
                r_lvl = str(row["risk"])

                h = upsert_accident_hotspot(
                    db=db,
                    start_location=s_name,
                    end_location=e_name,
                    start_latitude=s_lat,
                    start_longitude=s_lng,
                    end_latitude=e_lat,
                    end_longitude=e_lng,
                    risk_level=r_lvl,
                    risk_score=avg_risk,
                    accident_count=acc_cnt,
                    calculated_at=now,
                )
                persisted.append(h)
    except Exception as exc:
        logger.warning("Could not sync route hotspots: %s", exc)

    # 2. Also ensure real recorded zone accident counts from PostgreSQL are represented
    real_zone_accidents = (
        db.query(
            TrafficZone.zone_id,
            TrafficZone.zone_name,
            TrafficZone.location,
            func.count(Accident.accident_id).label("acc_count"),
        )
        .join(Road, Road.zone_id == TrafficZone.zone_id)
        .outerjoin(Accident, Accident.road_id == Road.road_id)
        .group_by(TrafficZone.zone_id, TrafficZone.zone_name, TrafficZone.location)
        .order_by(func.count(Accident.accident_id).desc())
        .limit(20)
        .all()
    )

    pred_risk_rows = (
        db.query(
            Road.zone_id,
            func.avg(AccidentPrediction.risk_percentage)
        )
        .join(AccidentPrediction, Road.road_id == AccidentPrediction.start_road_id)
        .filter(Road.zone_id.isnot(None))
        .group_by(Road.zone_id)
        .all()
    )
    zone_pred_risks = {row[0]: float(row[1]) for row in pred_risk_rows if row[1] is not None}

    existing_hotspots = {
        h.zone_id: h for h in db.query(AccidentHotspot).filter(AccidentHotspot.zone_id.isnot(None)).all()
    }

    for zone_id, _zone_name, loc_geo, db_acc_count in real_zone_accidents:
        lat, lon = _read_point(loc_geo)
        avg_pred_risk = zone_pred_risks.get(zone_id)
        calc_risk_score = float(avg_pred_risk) if avg_pred_risk is not None else min(90.0, 35.0 + db_acc_count * 5.0)
        calc_risk_level = resolve_risk_level(calc_risk_score)

        hotspot = upsert_accident_hotspot(
            db=db,
            latitude=lat,
            longitude=lon,
            risk_level=calc_risk_level,
            risk_score=calc_risk_score,
            accident_count=int(db_acc_count),
            zone_id=zone_id,
            calculated_at=now,
            existing=existing_hotspots.get(zone_id),
        )
        persisted.append(hotspot)

    db.commit()
    logger.info("Successfully persisted %d accident hotspots into database.", len(persisted))
    return persisted
