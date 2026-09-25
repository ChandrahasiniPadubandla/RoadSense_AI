"""
LangChain tools for the RoadSense AI chatbot.

Every tool below is a thin wrapper around a service that ALREADY exists in
this repository:
  - resolve_route_bundle() / trigger_ml_traffic_model() / trigger_ml_accident_model()
    from app.ml.prediction_engine — the exact functions
    routers/traffic_predictions.py and routers/accident_predictions.py use.
  - Direct queries against the real SQLAlchemy models for live traffic,
    historical accidents, and hotspots.
  - dashboard.get_dashboard_stats() for system-wide KPI numbers.

No prediction logic is duplicated here, and no tool ever fabricates a
result — each one either returns real data/predictions or reports that the
data is unavailable, matching the project's no-mock-data requirement.

Each tool opens its own short-lived DB session (SessionLocal) since
LangChain tool functions run outside FastAPI's request/Depends lifecycle.
"""
from typing import Optional

from langchain_core.tools import tool

from app.database.connection import SessionLocal
from app.database.models import Road, TrafficRecord, Accident, AccidentHotspot, TrafficZone, Alert
from app.ml.prediction_engine import (
    resolve_route_bundle,
    trigger_ml_traffic_model,
    trigger_ml_accident_model,
)
from app.routers.dashboard import get_dashboard_stats


def _find_road(db, name: str) -> Optional[Road]:
    if not name:
        return None
    return db.query(Road).filter(Road.road_name.ilike(f"%{name}%")).first()


@tool
def list_roads() -> str:
    """List the road names known to RoadSense AI, so you know what exact
    names to use in other tools. Use this if you're unsure whether a road
    the user mentioned actually exists in the system."""
    db = SessionLocal()
    try:
        roads = db.query(Road).filter(Road.is_active.is_(True)).limit(30).all()
        if not roads:
            return "No roads are currently registered in RoadSense AI."
        return "Known roads: " + ", ".join(r.road_name for r in roads)
    finally:
        db.close()


@tool
def get_current_traffic_condition(road_name: str) -> str:
    """Get the LIVE/current traffic reading (vehicle count, average speed,
    congestion level, weather) for a named road — the most recent recorded
    telemetry, not a prediction. Use this when the user asks about current
    or right-now traffic. If there is no recent reading, say so honestly."""
    db = SessionLocal()
    try:
        road = _find_road(db, road_name)
        if not road:
            return f"'{road_name}' does not match any road in RoadSense AI. Try list_roads to see known road names."

        record = (
            db.query(TrafficRecord)
            .filter(TrafficRecord.road_id == road.road_id)
            .order_by(TrafficRecord.timestamp.desc())
            .first()
        )
        if not record:
            return f"Live traffic data is currently unavailable for {road.road_name} — no recorded readings yet."

        return (
            f"LIVE reading for {road.road_name} (recorded {record.timestamp}): "
            f"{record.vehicle_count} vehicles, average speed {record.average_speed} km/h, "
            f"congestion level {record.congestion_level}, weather {record.weather_condition or 'unknown'}."
        )
    finally:
        db.close()


@tool
def get_road_traffic_prediction(road_name: str) -> str:
    """Run the REAL trained traffic congestion prediction model for a single
    named road (not a route). Returns the predicted congestion level and
    estimated time window. Use this when the user names one specific road
    and asks about predicted/future congestion."""
    db = SessionLocal()
    try:
        road = _find_road(db, road_name)
        if not road:
            return f"'{road_name}' does not match any road in RoadSense AI. Try list_roads to see known road names."

        bundle = resolve_route_bundle(db=db, road_id=road.road_id)
        result = trigger_ml_traffic_model(bundle)
        return (
            f"Traffic congestion prediction for {road.road_name}: "
            f"{result['congestion_level']} congestion expected {result['estimated_time']} "
            f"(model confidence {result.get('confidence_score', 'n/a')}%, source: {result.get('ml_source')})."
        )
    except Exception as exc:
        return f"I couldn't retrieve the required RoadSense traffic prediction right now ({exc.__class__.__name__})."
    finally:
        db.close()


@tool
def get_road_accident_risk(road_name: str) -> str:
    """Run the REAL trained accident risk prediction model for a single
    named road (not a route). Returns the predicted risk percentage and
    risk level. Use this when the user names one specific road and asks
    about accident risk or safety."""
    db = SessionLocal()
    try:
        road = _find_road(db, road_name)
        if not road:
            return f"'{road_name}' does not match any road in RoadSense AI. Try list_roads to see known road names."

        bundle = resolve_route_bundle(db=db, road_id=road.road_id)
        result = trigger_ml_accident_model(bundle)
        return (
            f"Accident risk prediction for {road.road_name}: "
            f"{result['risk_percentage']}% risk ({result['risk_level']}), "
            f"model confidence {result.get('confidence_score', 'n/a')}%, source: {result.get('ml_source')}."
        )
    except Exception as exc:
        return f"I couldn't retrieve the required RoadSense accident-risk prediction right now ({exc.__class__.__name__})."
    finally:
        db.close()


@tool
def get_route_traffic_prediction(start_location: str, end_location: str) -> str:
    """Run the REAL trained traffic congestion prediction model for a route
    given a start_location and end_location (place names). Use this
    whenever the user asks about traffic 'from A to B'."""
    db = SessionLocal()
    try:
        bundle = resolve_route_bundle(db=db, start_name=start_location, end_name=end_location)
        result = trigger_ml_traffic_model(bundle)
        return (
            f"Route traffic prediction from {bundle['start_label']} to {bundle['end_label']} "
            f"(~{bundle['distance_km']} km, matched to road {bundle['road_conditions']['road_name']}): "
            f"{result['congestion_level']} congestion expected {result['estimated_time']} "
            f"(confidence {result.get('confidence_score', 'n/a')}%)."
        )
    except Exception as exc:
        return f"I couldn't retrieve the required RoadSense route traffic prediction right now ({exc.__class__.__name__})."
    finally:
        db.close()


@tool
def get_route_accident_risk(start_location: str, end_location: str) -> str:
    """Run the REAL trained accident risk prediction model for a route given
    a start_location and end_location (place names). Use this whenever the
    user asks about accident risk 'from A to B' or for a route already
    discussed."""
    db = SessionLocal()
    try:
        bundle = resolve_route_bundle(db=db, start_name=start_location, end_name=end_location)
        result = trigger_ml_accident_model(bundle)
        return (
            f"Route accident risk prediction from {bundle['start_label']} to {bundle['end_label']} "
            f"(~{bundle['distance_km']} km, matched to road {bundle['road_conditions']['road_name']}): "
            f"{result['risk_percentage']}% risk ({result['risk_level']}), "
            f"confidence {result.get('confidence_score', 'n/a')}%."
        )
    except Exception as exc:
        return f"I couldn't retrieve the required RoadSense route accident-risk prediction right now ({exc.__class__.__name__})."
    finally:
        db.close()


@tool
def get_accident_hotspots(limit: int = 5) -> str:
    """List the top REAL accident hotspot zones by recorded accident count.
    Use this when asked which areas/zones have the highest accident risk or
    are accident-prone. If no hotspot data has been calculated yet, this
    tool says so rather than returning placeholder data."""
    db = SessionLocal()
    try:
        rows = (
            db.query(AccidentHotspot, TrafficZone.zone_name)
            .outerjoin(TrafficZone, TrafficZone.zone_id == AccidentHotspot.zone_id)
            .order_by(AccidentHotspot.accident_count.desc())
            .limit(max(1, min(limit, 20)))
            .all()
        )
        if not rows:
            return "No accident hotspot data has been calculated yet in RoadSense AI."
        lines = [
            f"- {zone_name or 'Unnamed zone'}: {h.accident_count or 0} recorded accidents, risk level {h.risk_level or 'unknown'}"
            for h, zone_name in rows
        ]
        return "Top accident hotspots (real, calculated data):\n" + "\n".join(lines)
    finally:
        db.close()


@tool
def get_historical_accident_data(road_name: str) -> str:
    """Get REAL historical accident records for a named road — count and
    severity breakdown from the accidents table. Use this for 'historical'
    or 'trend' questions about a specific road, as opposed to a live/predicted
    answer."""
    db = SessionLocal()
    try:
        road = _find_road(db, road_name)
        if not road:
            return f"'{road_name}' does not match any road in RoadSense AI. Try list_roads to see known road names."

        records = db.query(Accident).filter(Accident.road_id == road.road_id).all()
        if not records:
            return f"No historical accident records exist for {road.road_name} in RoadSense AI."

        severities = {}
        for a in records:
            key = (a.severity or "unknown").upper()
            severities[key] = severities.get(key, 0) + 1
        breakdown = ", ".join(f"{k}: {v}" for k, v in severities.items())
        return f"{road.road_name} has {len(records)} recorded historical accidents. Severity breakdown — {breakdown}."
    finally:
        db.close()


@tool
def get_active_alerts(road_name: Optional[str] = None, limit: int = 10) -> str:
    """Get REAL active alerts from the alerts table (accident, congestion,
    road, or emergency alerts that are currently ACTIVE, not yet resolved).
    Optionally pass road_name to filter to alerts for one specific road. Use
    this when the user asks what alerts/warnings are currently active, or
    whether a specific road has any active alert."""
    db = SessionLocal()
    try:
        query = db.query(Alert).filter(Alert.status == "ACTIVE")

        if road_name:
            road = _find_road(db, road_name)
            if not road:
                return f"'{road_name}' does not match any road in RoadSense AI. Try list_roads to see known road names."
            query = query.filter(Alert.road_id == road.road_id)

        alerts = (
            query
            .order_by(Alert.created_at.desc())
            .limit(max(1, min(limit, 30)))
            .all()
        )
        if not alerts:
            scope = f" for {road_name}" if road_name else ""
            return f"There are no active alerts{scope} in RoadSense AI right now."

        lines = []
        for a in alerts:
            road_label = a.road.road_name if a.road else "Unknown road"
            lines.append(
                f"- [{a.severity or 'unknown'}] {a.alert_type or 'ALERT'} on {road_label}: "
                f"{a.message or 'No description'} (raised {a.created_at})"
            )
        return "Active alerts (real, from the database):\n" + "\n".join(lines)
    finally:
        db.close()


@tool
def get_traffic_statistics() -> str:
    """Get REAL system-wide traffic and accident KPI statistics (active
    roads, roads with high traffic, accident alerts, high-risk zones, total
    accidents, accidents today, average system speed). Use this for
    dashboard-style or system-overview questions."""
    db = SessionLocal()
    try:
        stats = get_dashboard_stats(db=db)
        return (
            f"RoadSense system statistics — active roads: {stats.active_roads}/{stats.total_roads}, "
            f"roads with high/severe traffic: {stats.high_traffic_roads}, "
            f"accident alerts needing attention: {stats.accident_alerts}, "
            f"high-risk zones: {stats.high_risk_zones}, "
            f"total recorded accidents: {stats.total_accidents} ({stats.accidents_today} today), "
            f"average system speed: {stats.average_system_speed} km/h."
        )
    except Exception as exc:
        return f"RoadSense data could not be retrieved right now ({exc.__class__.__name__})."
    finally:
        db.close()


ALL_TOOLS = [
    list_roads,
    get_current_traffic_condition,
    get_road_traffic_prediction,
    get_road_accident_risk,
    get_route_traffic_prediction,
    get_route_accident_risk,
    get_accident_hotspots,
    get_historical_accident_data,
    get_active_alerts,
    get_traffic_statistics,
]
