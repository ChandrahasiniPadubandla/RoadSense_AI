from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    Accident,
    AccidentHotspot,
    TrafficZone
)
from app.schemas.dashboard import DashboardStatsResponse


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get Smart Traffic Dashboard KPI Statistics"
)
def get_dashboard_stats(
    db: Session = Depends(get_db)
):
    """
    Returns real-time dashboard statistics and counters as specified in DPR Module 15:
    - active_roads: count of active road segments
    - total_roads: total registered roads
    - high_traffic_roads: roads currently experiencing HIGH or SEVERE congestion
    - accident_alerts: severe or fatal accidents requiring urgent attention
    - high_risk_zones: count of accident hotspots / high risk zones
    - total_accidents: all recorded accident incidents
    - accidents_today: accidents occurred in the last 24 hours
    - total_traffic_records: total traffic observations
    - average_system_speed: average speed across active roads
    """
    total_roads = db.query(Road).count()
    active_roads = db.query(Road).filter(Road.is_active == True).count()

    # Subquery for the most recent traffic record for each road
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

    high_traffic_roads = sum(
        1 for r in latest_records
        if (r.congestion_level and r.congestion_level.upper() in ["HIGH", "SEVERE"])
        or (r.traffic_density is not None and float(r.traffic_density) >= 70.0)
    )

    valid_speeds = [
        float(r.average_speed)
        for r in latest_records
        if r.average_speed is not None and float(r.average_speed) > 0
    ]
    avg_speed = round(sum(valid_speeds) / len(valid_speeds), 1) if valid_speeds else None

    # Accidents
    total_accidents = db.query(Accident).count()

    now = datetime.now()
    since_24h = now - timedelta(hours=24)
    accidents_today = (
        db.query(Accident)
        .filter(Accident.accident_datetime >= since_24h)
        .count()
    )

    accident_alerts = (
        db.query(Accident)
        .filter(Accident.severity.in_(["SEVERE", "FATAL", "Severe", "Fatal"]))
        .count()
    )

    # High-risk zones: hotspots or zones associated with accidents
    hotspot_count = (
        db.query(AccidentHotspot)
        .filter(AccidentHotspot.risk_level.in_(["HIGH", "CRITICAL", "High", "Critical"]))
        .count()
    )

    if hotspot_count > 0:
        high_risk_zones = hotspot_count
    else:
        zone_accident_count = (
            db.query(Road.zone_id)
            .join(Accident, Accident.road_id == Road.road_id)
            .filter(Road.zone_id.isnot(None))
            .distinct()
            .count()
        )
        high_risk_zones = zone_accident_count if zone_accident_count > 0 else db.query(TrafficZone).count()

    total_traffic_records = db.query(TrafficRecord).count()

    return DashboardStatsResponse(
        active_roads=active_roads,
        total_roads=total_roads,
        high_traffic_roads=high_traffic_roads,
        accident_alerts=accident_alerts,
        high_risk_zones=high_risk_zones,
        total_accidents=total_accidents,
        accidents_today=accidents_today,
        total_traffic_records=total_traffic_records,
        average_system_speed=avg_speed,
        timestamp=now
    )
