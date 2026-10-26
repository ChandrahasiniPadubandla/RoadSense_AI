import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    TrafficPrediction,
    Accident,
    AccidentHotspot,
    TrafficZone
)
from app.schemas.dashboard import DashboardStatsResponse


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

_STATS_CACHE = {"ts": 0.0, "data": None}
_CACHE_TTL_SECS = 15.0


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
    now_ts = time.time()
    if _STATS_CACHE["data"] is not None and (now_ts - _STATS_CACHE["ts"]) < _CACHE_TTL_SECS:
        return _STATS_CACHE["data"]

    now = datetime.now()
    since_24h = now - timedelta(hours=24)

    # 1. Consolidate ALL scalar counts into 1 single round-trip SQL query
    counts_res = db.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM roads) AS total_roads,
                (SELECT COUNT(*) FROM roads WHERE is_active = true) AS active_roads,
                (SELECT COUNT(*) FROM accidents) AS total_accidents,
                (SELECT COUNT(*) FROM accidents WHERE accident_datetime >= :since_24h) AS accidents_today,
                (SELECT COUNT(*) FROM accidents WHERE severity IN ('SEVERE', 'FATAL', 'Severe', 'Fatal')) AS accident_alerts,
                (SELECT COUNT(*) FROM accident_hotspots WHERE risk_level IN ('HIGH', 'CRITICAL', 'High', 'Critical', 'SEVERE', 'Severe')) AS hotspot_count,
                (SELECT COUNT(*) FROM traffic_records) AS total_traffic_records
        """),
        {"since_24h": since_24h}
    ).mappings().first()

    total_roads = counts_res["total_roads"] or 0
    active_roads = counts_res["active_roads"] or 0
    total_accidents = counts_res["total_accidents"] or 0
    accidents_today = counts_res["accidents_today"] or 0
    accident_alerts = counts_res["accident_alerts"] or 0
    hotspot_count = counts_res["hotspot_count"] or 0
    total_traffic_records = counts_res["total_traffic_records"] or 0

    # 2. Latest AI traffic predictions (fetching only required columns)
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
        db.query(TrafficPrediction.start_road_id, TrafficPrediction.predicted_congestion)
        .join(
            latest_pred_sub,
            and_(
                TrafficPrediction.start_road_id == latest_pred_sub.c.road_id,
                TrafficPrediction.created_at == latest_pred_sub.c.max_created
            )
        )
        .all()
    )
    pred_by_road = {p[0]: p[1] for p in latest_predictions if p[0] is not None}

    # 3. Latest traffic observations (fetching only required columns)
    latest_traffic_sub = (
        db.query(
            TrafficRecord.road_id,
            func.max(TrafficRecord.timestamp).label("max_ts")
        )
        .group_by(TrafficRecord.road_id)
        .subquery()
    )

    latest_records = (
        db.query(TrafficRecord.road_id, TrafficRecord.average_speed, TrafficRecord.congestion_level)
        .join(
            latest_traffic_sub,
            and_(
                TrafficRecord.road_id == latest_traffic_sub.c.road_id,
                TrafficRecord.timestamp == latest_traffic_sub.c.max_ts
            )
        )
        .all()
    )
    traffic_by_road = {r[0]: r for r in latest_records}

    # 4. Evaluate high traffic roads
    active_road_ids = [r[0] for r in db.query(Road.road_id).filter(Road.is_active.is_(True)).all()]
    high_traffic_roads = 0
    for r_id in active_road_ids:
        pred_cong = pred_by_road.get(r_id)
        tr = traffic_by_road.get(r_id)
        cong = None
        if pred_cong:
            cong = pred_cong.upper()
        elif tr and tr[2]:
            cong = tr[2].upper()
        if cong in ["HIGH", "SEVERE"]:
            high_traffic_roads += 1

    valid_speeds = [
        float(r[1])
        for r in latest_records
        if r[1] is not None and float(r[1]) > 0
    ]
    avg_speed = round(sum(valid_speeds) / len(valid_speeds), 1) if valid_speeds else None

    # 5. High-risk zones
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

    result = DashboardStatsResponse(
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
    _STATS_CACHE["ts"] = now_ts
    _STATS_CACHE["data"] = result
    return result


@router.get(
    "/summary",
    summary="Get Dashboard Summary Overview"
)
def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    """
    Returns dashboard summary counters for the frontend dashboard cards:
    active_roads, high_traffic_records, active_alerts, total_accidents, high_risk_zones.
    """
    stats = get_dashboard_stats(db=db)
    return {
        "active_roads": stats.active_roads,
        "total_roads": stats.total_roads,
        "high_traffic_records": stats.high_traffic_roads,
        "high_traffic_roads": stats.high_traffic_roads,
        "active_alerts": stats.accident_alerts,
        "total_accidents": stats.total_accidents,
        "high_risk_zones": stats.high_risk_zones,
        "accidents_today": stats.accidents_today,
        "total_traffic_records": stats.total_traffic_records,
        "average_system_speed": stats.average_system_speed,
        "timestamp": stats.timestamp.isoformat() if stats.timestamp else datetime.now().isoformat(),
    }


@router.get(
    "/trend",
    summary="Get Traffic Trend Data"
)
def get_dashboard_trend(
    db: Session = Depends(get_db)
):
    """
    Returns chronological hourly traffic volume trend aggregated across the system
    (last 24 intervals) for the dashboard trend line chart.
    """
    hourly_trends = (
        db.query(
            TrafficRecord.timestamp,
            func.sum(TrafficRecord.vehicle_count).label("total_vehicles"),
            func.avg(TrafficRecord.average_speed).label("avg_speed")
        )
        .group_by(TrafficRecord.timestamp)
        .order_by(TrafficRecord.timestamp.desc())
        .limit(24)
        .all()
    )

    if hourly_trends:
        return [
            {
                "timestamp": t.timestamp.isoformat() if t.timestamp else datetime.now().isoformat(),
                "vehicle_count": int(t.total_vehicles or 0),
                "average_speed": round(float(t.avg_speed), 1) if t.avg_speed is not None else 0.0,
                "road_id": "system_total"
            }
            for t in reversed(hourly_trends)
        ]

    # Fallback if no traffic records in DB yet
    now = datetime.now()
    return [
        {
            "timestamp": (now - timedelta(hours=i)).isoformat(),
            "vehicle_count": 0,
            "average_speed": 0.0,
            "road_id": "system"
        }
        for i in reversed(range(10))
    ]

