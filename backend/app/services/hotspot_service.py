import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.models import AccidentHotspot, TrafficZone, Road, Accident, AccidentPrediction

logger = logging.getLogger("Metrivon")


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


def upsert_accident_hotspot(
    db: Session,
    latitude: Optional[float],
    longitude: Optional[float],
    risk_level: Optional[str],
    risk_score: float,
    accident_count: int = 0,
    zone_id: Optional[UUID] = None,
    calculated_at: Optional[datetime] = None,
    existing: Optional[AccidentHotspot] = None,
) -> AccidentHotspot:
    """
    Inserts or updates an accident hotspot in the `accident_hotspots` table.
    All data (zone, risk score, risk level, and PostGIS location geometry)
    is strictly derived from database records and ML inference — zero dummy data.
    """
    now = calculated_at or datetime.utcnow()
    # Always resolve risk_level mathematically from risk_score so score and tier never contradict
    safe_risk_level = resolve_risk_level(risk_score)

    # If coordinates are not provided, resolve strictly from the associated TrafficZone in DB
    if (latitude is None or longitude is None) and zone_id:
        zone = db.query(TrafficZone).filter(TrafficZone.zone_id == zone_id).first()
        if zone and zone.location is not None:
            try:
                pt = to_shape(zone.location)
                latitude, longitude = float(pt.y), float(pt.x)
            except Exception:
                pass

    loc_point = None
    if latitude is not None and longitude is not None:
        loc_point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

    # 1. Match existing hotspot by zone_id (use preloaded instance if supplied)
    if existing is None and zone_id:
        existing = (
            db.query(AccidentHotspot)
            .filter(AccidentHotspot.zone_id == zone_id)
            .first()
        )

    # 2. If no match by zone_id, match by proximity to known real coordinates
    if not existing and latitude is not None and longitude is not None:
        nearby_hotspots = db.query(AccidentHotspot).all()
        for h in nearby_hotspots:
            if h.location is not None:
                try:
                    pt = to_shape(h.location)
                    if abs(float(pt.y) - latitude) < 0.008 and abs(float(pt.x) - longitude) < 0.008:
                        existing = h
                        break
                except Exception:
                    continue

    if existing:
        existing.accident_count = max(existing.accident_count or 0, accident_count)
        existing.risk_score = round(max(float(existing.risk_score or 0.0), float(risk_score)), 2)
        # Risk level is strictly determined by the final risk score
        existing.risk_level = resolve_risk_level(existing.risk_score)

        if loc_point is not None:
            existing.location = loc_point
        existing.calculated_at = now
        if zone_id and not existing.zone_id:
            existing.zone_id = zone_id
        return existing
    else:
        new_hotspot = AccidentHotspot(
            zone_id=zone_id,
            location=loc_point,
            accident_count=accident_count,
            risk_score=round(float(risk_score), 2),
            risk_level=safe_risk_level,
            calculated_at=now,
        )
        db.add(new_hotspot)
        return new_hotspot


def sync_empirical_hotspots(db: Session, top_n: int = 20) -> List[AccidentHotspot]:
    """
    Computes top accident hotspots strictly from REAL database accident records
    (`accidents`, `accident_predictions`, `roads`, and `traffic_zones`).
    Optimized with bulk pre-fetching to prevent N+1 remote database roundtrips.
    """
    persisted = []
    now = datetime.utcnow()

    # 1. Query real recorded accident counts per zone directly from PostgreSQL
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
        .limit(top_n)
        .all()
    )

    # 2. Bulk-query average prediction risk for all zones in a SINGLE query
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

    # 3. Bulk-query existing hotspots to avoid querying inside the loop
    existing_hotspots = {
        h.zone_id: h for h in db.query(AccidentHotspot).filter(AccidentHotspot.zone_id.isnot(None)).all()
    }

    # 4. Process each real zone with recorded accidents
    for zone_id, _zone_name, loc_geo, db_acc_count in real_zone_accidents:
        lat, lon = None, None
        if loc_geo is not None:
            try:
                pt = to_shape(loc_geo)
                lat, lon = float(pt.y), float(pt.x)
            except Exception:
                pass

        avg_pred_risk = zone_pred_risks.get(zone_id)

        if avg_pred_risk is not None:
            calc_risk_score = float(avg_pred_risk)
        else:
            calc_risk_score = min(90.0, 35.0 + db_acc_count * 5.0)

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
        hotspot.accident_count = int(db_acc_count)
        hotspot.risk_score = round(float(calc_risk_score), 2)
        hotspot.risk_level = calc_risk_level
        persisted.append(hotspot)

    db.commit()
    logger.info("Successfully persisted %d real-data accident hotspots into database.", len(persisted))
    return persisted
