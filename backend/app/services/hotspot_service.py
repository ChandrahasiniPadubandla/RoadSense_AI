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
    start_location: Optional[str] = None,
    end_location: Optional[str] = None,
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
    end_lat: Optional[float] = None,
    end_lng: Optional[float] = None,
    zone_id: Optional[UUID] = None,
) -> Optional[Dict[str, Any]]:
    """
    Finds whether the specified route corridor (defined by start_location and end_location
    and/or start/end coordinates) matches a known accident hotspot.
    """
    clean_s = (start_location or "").strip().lower()
    clean_e = (end_location or "").strip().lower()

    # 1. Exact or partial match on route start and end locations in DB
    if clean_s and clean_e:
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
            .order_by(AccidentHotspot.accident_count.desc(), AccidentHotspot.risk_score.desc())
            .first()
        )
        if db_match:
            lat, lon = _read_point(db_match.location)
            return {
                "hotspot_id": str(db_match.hotspot_id),
                "start_location": db_match.start_location or start_location,
                "end_location": db_match.end_location or end_location,
                "accident_count": int(db_match.accident_count or 0),
                "risk_score": float(db_match.risk_score) if db_match.risk_score is not None else None,
                "risk_level": db_match.risk_level or resolve_risk_level(db_match.risk_score or 0.0),
                "latitude": lat,
                "longitude": lon,
            }

    # 2. Check CSV-generated empirical hotspots if not yet in database
    if clean_s and clean_e and os.path.exists(CSV_HOTSPOT_PATH):
        try:
            import pandas as pd
            df = pd.read_csv(CSV_HOTSPOT_PATH)
            # Direct match
            m = df[
                df["start_location"].str.lower().str.contains(clean_s, na=False, regex=False)
                & df["end_location"].str.lower().str.contains(clean_e, na=False, regex=False)
            ]
            if m.empty:
                # Reverse match
                m = df[
                    df["start_location"].str.lower().str.contains(clean_e, na=False, regex=False)
                    & df["end_location"].str.lower().str.contains(clean_s, na=False, regex=False)
                ]
            if not m.empty:
                row = m.iloc[0]
                s_name = str(row["start_location"])
                e_name = str(row["end_location"])
                s_lat = float(row["start_latitude"])
                s_lng = float(row["start_longitude"])
                e_lat = float(row["end_latitude"])
                e_lng = float(row["end_longitude"])
                acc_cnt = int(row["accidents"])
                avg_risk = float(row["average_risk"])
                r_lvl = str(row["risk"])

                # Persist it into DB so next query is instant
                persisted = upsert_accident_hotspot(
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
                    zone_id=zone_id,
                )
                db.commit()

                lat, lon = _read_point(persisted.location)
                return {
                    "hotspot_id": str(persisted.hotspot_id),
                    "start_location": s_name,
                    "end_location": e_name,
                    "accident_count": acc_cnt,
                    "risk_score": avg_risk,
                    "risk_level": r_lvl,
                    "latitude": lat,
                    "longitude": lon,
                }
        except Exception as exc:
            logger.warning("Error searching CSV hotspots: %s", exc)

    # 3. Match by spatial coordinate proximity (corridor start and end within ~1.5km)
    if start_lat is not None and start_lng is not None and end_lat is not None and end_lng is not None:
        all_hotspots = (
            db.query(AccidentHotspot)
            .filter(AccidentHotspot.start_latitude.isnot(None), AccidentHotspot.end_latitude.isnot(None))
            .all()
        )
        for h in all_hotspots:
            try:
                hs_lat = float(h.start_latitude)
                hs_lng = float(h.start_longitude)
                he_lat = float(h.end_latitude)
                he_lng = float(h.end_longitude)

                # Direct match within ~0.015 deg (~1.5 km)
                is_direct = (abs(hs_lat - start_lat) < 0.015 and abs(hs_lng - start_lng) < 0.015 and
                             abs(he_lat - end_lat) < 0.015 and abs(he_lng - end_lng) < 0.015)
                is_reverse = (abs(hs_lat - end_lat) < 0.015 and abs(hs_lng - end_lng) < 0.015 and
                              abs(he_lat - start_lat) < 0.015 and abs(he_lng - start_lng) < 0.015)

                if is_direct or is_reverse:
                    lat, lon = _read_point(h.location)
                    return {
                        "hotspot_id": str(h.hotspot_id),
                        "start_location": h.start_location or start_location,
                        "end_location": h.end_location or end_location,
                        "accident_count": int(h.accident_count or 0),
                        "risk_score": float(h.risk_score) if h.risk_score is not None else None,
                        "risk_level": h.risk_level or resolve_risk_level(h.risk_score or 0.0),
                        "latitude": lat,
                        "longitude": lon,
                    }
            except Exception:
                continue

    # 4. Fallback to zone-level hotspot if road is associated with a traffic zone
    if zone_id:
        zh = (
            db.query(AccidentHotspot)
            .filter(AccidentHotspot.zone_id == zone_id)
            .order_by(AccidentHotspot.accident_count.desc(), AccidentHotspot.calculated_at.desc())
            .first()
        )
        if zh is not None:
            lat, lon = _read_point(zh.location)
            return {
                "hotspot_id": str(zh.hotspot_id),
                "start_location": zh.start_location or start_location,
                "end_location": zh.end_location or end_location,
                "accident_count": int(zh.accident_count or 0),
                "risk_score": float(zh.risk_score) if zh.risk_score is not None else None,
                "risk_level": zh.risk_level or resolve_risk_level(zh.risk_score or 0.0),
                "latitude": lat,
                "longitude": lon,
            }

    return None


def sync_empirical_hotspots(db: Session, top_n: int = 50) -> List[AccidentHotspot]:
    """
    Synchronizes accident hotspots into the PostgreSQL database.
    Integrates route-level hotspots (start_location -> end_location) from
    accident_hotspots.csv as well as real zone-level accident records.
    """
    persisted = []
    now = datetime.utcnow()

    # 1. First, sync route-level hotspots from accident_hotspots.csv if present
    if os.path.exists(CSV_HOTSPOT_PATH):
        try:
            import pandas as pd
            df = pd.read_csv(CSV_HOTSPOT_PATH)
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
            logger.warning("Could not sync CSV hotspots: %s", exc)

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
