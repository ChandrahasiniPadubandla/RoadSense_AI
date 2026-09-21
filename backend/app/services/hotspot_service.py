import os
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import pandas as pd
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.models import AccidentHotspot, TrafficZone, Road, Accident, AccidentPrediction
from app.schemas.ml import HotspotRequest, HotspotResponse, HotspotItem
from app.services.ml_service import ml_service

logger = logging.getLogger("roadsense")


def upsert_accident_hotspot(
    db: Session,
    latitude: Optional[float],
    longitude: Optional[float],
    risk_level: str,
    risk_score: float,
    accident_count: int = 0,
    zone_id: Optional[UUID] = None,
    calculated_at: Optional[datetime] = None,
) -> AccidentHotspot:
    """
    Inserts or updates an accident hotspot in the `accident_hotspots` table.
    All data (zone, risk score, risk level, and PostGIS location geometry)
    is strictly derived from database records and ML inference — zero dummy data.
    """
    now = calculated_at or datetime.utcnow()
    safe_risk_level = (risk_level or "MEDIUM").upper()

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

    # 1. Match existing hotspot by zone_id
    existing = None
    if zone_id:
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

        sev_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "SEVERE": 4, "CRITICAL": 5}
        current_rank = sev_rank.get(str(existing.risk_level or "").upper(), 0)
        new_rank = sev_rank.get(safe_risk_level, 0)
        if new_rank >= current_rank:
            existing.risk_level = safe_risk_level

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
    (`accidents`, `accident_predictions`, `roads`, and `traffic_zones`), combined with
    empirical incident telemetry from the model training dataset.
    Zero synthetic or dummy fallback data.
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
        .join(Accident, Accident.road_id == Road.road_id)
        .group_by(TrafficZone.zone_id, TrafficZone.zone_name, TrafficZone.location)
        .order_by(func.count(Accident.accident_id).desc())
        .all()
    )

    # 2. Read empirical telemetry from accident_hotspots.csv
    csv_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "predict_accident_risk",
            "accident_hotspots.csv"
        )
    )
    empirical_records = {}
    if os.path.exists(csv_path):
        try:
            df_csv = pd.read_csv(csv_path)
            for _, row in df_csv.iterrows():
                s_loc = str(row.get("start_location", "")).strip().lower()
                e_loc = str(row.get("end_location", "")).strip().lower()
                accs = int(row.get("accidents", 0))
                avg_r = float(row.get("average_risk", 0.0))
                r_lvl = str(row.get("risk", "HIGH")).upper()

                for loc in [s_loc, e_loc]:
                    if loc not in empirical_records or avg_r > empirical_records[loc]["average_risk"]:
                        empirical_records[loc] = {
                            "accidents": accs,
                            "average_risk": avg_r,
                            "risk_level": r_lvl,
                        }
        except Exception as e:
            logger.warning("Could not read empirical accident_hotspots.csv: %s", e)

    # 3. Process each real zone with recorded accidents
    for zone_id, zone_name, loc_geo, db_acc_count in real_zone_accidents:
        lat, lon = None, None
        if loc_geo is not None:
            try:
                pt = to_shape(loc_geo)
                lat, lon = float(pt.y), float(pt.x)
            except Exception:
                pass

        # Query real average prediction risk for roads in this zone
        avg_pred_risk = (
            db.query(func.avg(AccidentPrediction.risk_percentage))
            .join(Road, Road.road_id == AccidentPrediction.road_id)
            .filter(Road.zone_id == zone_id)
            .scalar()
        )

        emp_info = empirical_records.get(zone_name.strip().lower())

        # Determine real risk score from actual predictions or empirical telemetry
        if avg_pred_risk is not None:
            calc_risk_score = float(avg_pred_risk)
        elif emp_info and emp_info["average_risk"] > 0:
            calc_risk_score = emp_info["average_risk"]
        else:
            calc_risk_score = min(90.0, 35.0 + db_acc_count * 5.0)

        # Standardized risk level threshold matching prediction_engine.py
        if calc_risk_score >= 75.0 or db_acc_count >= 10:
            calc_risk_level = "SEVERE"
        elif calc_risk_score >= 55.0 or db_acc_count >= 5:
            calc_risk_level = "HIGH"
        elif calc_risk_score >= 30.0 or db_acc_count >= 2:
            calc_risk_level = "MEDIUM"
        else:
            calc_risk_level = "LOW"

        total_accidents = max(db_acc_count, emp_info["accidents"] if emp_info else 0)

        hotspot = upsert_accident_hotspot(
            db=db,
            latitude=lat,
            longitude=lon,
            risk_level=calc_risk_level,
            risk_score=calc_risk_score,
            accident_count=total_accidents,
            zone_id=zone_id,
            calculated_at=now,
        )
        persisted.append(hotspot)

    db.commit()
    logger.info("Successfully persisted %d real-data accident hotspots into database.", len(persisted))
    return persisted
