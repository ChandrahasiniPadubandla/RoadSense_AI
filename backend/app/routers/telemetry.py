from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Road, TrafficRecord, Accident, Alert
from app.services.setup_service import build_readiness_report
from app.services.weather import get_live_weather

router = APIRouter(
    prefix="/public",
    tags=["Public Telemetry"]
)


@router.get(
    "/readiness",
    summary="Check that shared database, geocoding scope, and artifacts are configured"
)
def get_public_readiness(db: Session = Depends(get_db)):
    """
    Startup/configuration check for reproducibility. Confirms the backend can see
    the shared project database (same roads/traffic/accidents for everyone),
    reports the Hyderabad suggestion boundary, and flags optional integrations.
    """
    return build_readiness_report(db)


@router.get(
    "/telemetry",
    summary="Get live database metrics, real monitored road corridors, and live weather"
)
def get_public_telemetry(db: Session = Depends(get_db)):
    total_roads = db.query(Road).count()
    active_roads = db.query(Road).filter(Road.is_active.is_(True)).count()
    total_traffic = db.query(TrafficRecord).count()
    total_accidents = db.query(Accident).count()
    total_alerts = db.query(Alert).filter(Alert.status == "ACTIVE").count()

    real_roads = (
        db.query(Road)
        .filter(Road.is_active.is_(True))
        .order_by(Road.road_name.asc())
        .limit(6)
        .all()
    )

    corridors = []
    for r in real_roads:
        latest_record = (
            db.query(TrafficRecord)
            .filter(TrafficRecord.road_id == r.road_id)
            .order_by(TrafficRecord.timestamp.desc())
            .first()
        )
        corridors.append({
            "road_id": str(r.road_id),
            "name": r.road_name,
            "type": r.road_type,
            "speed_limit": float(r.speed_limit) if r.speed_limit is not None else None,
            "lanes": r.number_of_lanes,
            "capacity": r.road_capacity,
            "condition": r.road_condition,
            "observed_speed": float(latest_record.average_speed) if latest_record and latest_record.average_speed is not None else None,
            "congestion_level": latest_record.congestion_level if latest_record and latest_record.congestion_level else None,
            "traffic_density": float(latest_record.traffic_density) if latest_record and latest_record.traffic_density is not None else None,
            "vehicle_count": latest_record.vehicle_count if latest_record and latest_record.vehicle_count is not None else None,
        })

    try:
        live_weather = get_live_weather(17.4156, 78.4347)
    except Exception as exc:
        live_weather = {
            "weather_condition": None,
            "temperature": None,
            "source": "Open-Meteo",
            "is_live": False,
            "error": str(exc)
        }

    return {
        "status": "OPERATIONAL",
        "counts": {
            "total_roads": total_roads,
            "active_roads": active_roads,
            "total_traffic_observations": total_traffic,
            "total_recorded_accidents": total_accidents,
            "active_alerts": total_alerts,
        },
        "corridors": corridors,
        "weather": live_weather,
    }