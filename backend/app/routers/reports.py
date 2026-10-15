import csv
import io
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    Accident,
    AccidentHotspot,
    TrafficPrediction,
    AccidentPrediction,
    TrafficZone,
    User
)
from app.security import require_roles


router = APIRouter(
    prefix="/reports",
    tags=["Reports & Analytics Export"],
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)


def _generate_csv_response(filename: str, headers: list[str], rows: list[list[Any]]) -> Response:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([str(cell) if cell is not None else "" for cell in row])

    csv_data = output.getvalue()
    output.close()

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )


def _page_envelope(items: list, total: int, page: int, page_size: int) -> dict:
    """Standard paginated JSON envelope used by the Reports preview."""
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get(
    "/export",
    summary="Export Traffic, Accident, Hotspot, and Prediction Reports",
    description=(
        "Generates downloadable analytical reports in CSV or JSON format. "
        "Restricted to SUPER_ADMIN and TRAFFIC_AUTHORITY roles."
    )
)
@router.get(
    "",
    summary="Export Traffic, Accident, Hotspot, and Prediction Reports (Root Route)",
    include_in_schema=False
)
def export_report(
    report_type: str = Query(
        "summary",
        description="Type of report: 'accidents', 'traffic', 'hotspots', 'predictions', or 'summary'"
    ),
    format: str = Query(
        "csv",
        description="Output format: 'csv' (downloadable file) or 'json'"
    ),
    start_date: Optional[datetime] = Query(None, description="Filter records starting from this ISO datetime"),
    end_date: Optional[datetime] = Query(None, description="Filter records up to this ISO datetime"),
    limit: int = Query(1000, ge=1, le=10000, description="Max rows to export (CSV / unpaginated JSON)"),
    page: Optional[int] = Query(
        None, ge=1,
        description="1-based page number. When supplied with format=json, the response is a paginated envelope "
                    "{items, total, page, page_size, total_pages} using SQL OFFSET/LIMIT."
    ),
    page_size: int = Query(20, ge=1, le=200, description="Rows per page when `page` is supplied"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))
):
    rtype = report_type.strip().lower()
    fmt = format.strip().lower()
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    paginated = fmt == "json" and page is not None

    # =========================================================
    # 1. ACCIDENTS REPORT
    # =========================================================
    if rtype == "accidents":
        query = (
            db.query(Accident, Road.road_name)
            .outerjoin(Road, Accident.road_id == Road.road_id)
        )
        if start_date:
            query = query.filter(Accident.accident_datetime >= start_date)
        if end_date:
            query = query.filter(Accident.accident_datetime <= end_date)

        query = query.order_by(Accident.accident_datetime.desc())
        if paginated:
            total = query.order_by(None).count()
            records = query.offset((page - 1) * page_size).limit(page_size).all()
        else:
            records = query.limit(limit).all()

        if fmt == "json":
            items = [
                {
                    "accident_id": str(a.accident_id),
                    "road_name": road_name or "Unknown Road",
                    "accident_time": a.accident_datetime.isoformat() if a.accident_datetime else None,
                    "severity": a.severity,
                    "fatalities": a.fatalities or 0,
                    "injuries": a.injuries or 0,
                    "vehicle_count": a.vehicle_count or 0,
                    "weather_condition": a.weather_condition,
                    "road_condition": a.road_condition,
                    "description": a.description
                }
                for a, road_name in records
            ]
            return _page_envelope(items, total, page, page_size) if paginated else items

        csv_headers = [
            "Accident ID",
            "Road Name",
            "Accident Datetime",
            "Severity",
            "Fatalities",
            "Injuries",
            "Vehicles Involved",
            "Weather Condition",
            "Road Condition",
            "Description"
        ]
        csv_rows = [
            [
                a.accident_id,
                road_name or "Unknown",
                a.accident_datetime.isoformat() if a.accident_datetime else "",
                a.severity or "UNKNOWN",
                a.fatalities or 0,
                a.injuries or 0,
                a.vehicle_count or 1,
                a.weather_condition or "",
                a.road_condition or "",
                a.description or ""
            ]
            for a, road_name in records
        ]
        return _generate_csv_response(f"Metrivon_accidents_{timestamp_str}.csv", csv_headers, csv_rows)

    # =========================================================
    # 2. TRAFFIC OBSERVATIONS REPORT
    # =========================================================
    elif rtype == "traffic":
        query = (
            db.query(TrafficRecord, Road.road_name)
            .outerjoin(Road, TrafficRecord.road_id == Road.road_id)
        )
        if start_date:
            query = query.filter(TrafficRecord.timestamp >= start_date)
        if end_date:
            query = query.filter(TrafficRecord.timestamp <= end_date)

        query = query.order_by(TrafficRecord.timestamp.desc())
        if paginated:
            total = query.order_by(None).count()
            records = query.offset((page - 1) * page_size).limit(page_size).all()
        else:
            records = query.limit(limit).all()

        if fmt == "json":
            items = [
                {
                    "traffic_id": str(tr.traffic_id),
                    "road_name": road_name or "Unknown Road",
                    "timestamp": tr.timestamp.isoformat() if tr.timestamp else None,
                    "vehicle_count": tr.vehicle_count,
                    "average_speed_kmh": float(tr.average_speed) if tr.average_speed is not None else None,
                    "traffic_density": float(tr.traffic_density) if tr.traffic_density is not None else None,
                    "congestion_level": tr.congestion_level,
                    "road_condition": tr.road_condition,
                    "weather_condition": tr.weather_condition,
                    "rainfall_mm": float(tr.rainfall) if tr.rainfall is not None else None,
                    "temperature_c": float(tr.temperature) if tr.temperature is not None else None,
                    "is_holiday": tr.is_holiday
                }
                for tr, road_name in records
            ]
            return _page_envelope(items, total, page, page_size) if paginated else items

        csv_headers = [
            "Traffic ID",
            "Road Name",
            "Observation Timestamp",
            "Vehicle Count",
            "Avg Speed (km/h)",
            "Traffic Density (%)",
            "Congestion Level",
            "Road Condition",
            "Weather",
            "Rainfall (mm)",
            "Temperature (C)",
            "Is Holiday"
        ]
        csv_rows = [
            [
                tr.traffic_id,
                road_name or "Unknown",
                tr.timestamp.isoformat() if tr.timestamp else "",
                tr.vehicle_count,
                round(float(tr.average_speed), 1) if tr.average_speed is not None else "",
                round(float(tr.traffic_density), 1) if tr.traffic_density is not None else "",
                tr.congestion_level or "LOW",
                tr.road_condition or "",
                tr.weather_condition or "",
                tr.rainfall if tr.rainfall is not None else "",
                tr.temperature if tr.temperature is not None else "",
                "Yes" if tr.is_holiday else "No"
            ]
            for tr, road_name in records
        ]
        return _generate_csv_response(f"Metrivon_traffic_{timestamp_str}.csv", csv_headers, csv_rows)

    # =========================================================
    # 3. ACCIDENT HOTSPOTS REPORT
    # =========================================================
    elif rtype == "hotspots":
        query = (
            db.query(AccidentHotspot, TrafficZone.zone_name)
            .outerjoin(TrafficZone, AccidentHotspot.zone_id == TrafficZone.zone_id)
        )
        query = query.order_by(AccidentHotspot.accident_count.desc())
        if paginated:
            total = query.order_by(None).count()
            records = query.offset((page - 1) * page_size).limit(page_size).all()
        else:
            records = query.all()

        if fmt == "json":
            items = [
                {
                    "hotspot_id": str(h.hotspot_id),
                    "zone_name": zone_name or "General Area",
                    "accident_count": h.accident_count,
                    "risk_score": float(h.risk_score) if h.risk_score is not None else None,
                    "risk_level": h.risk_level or "MODERATE",
                    "calculated_at": h.calculated_at.isoformat() if h.calculated_at else None
                }
                for h, zone_name in records
            ]
            return _page_envelope(items, total, page, page_size) if paginated else items

        csv_headers = [
            "Hotspot ID",
            "Zone / Area Name",
            "Total Accidents Recorded",
            "Risk Score",
            "Risk Level",
            "Last Calculated"
        ]
        csv_rows = [
            [
                h.hotspot_id,
                zone_name or "General Area",
                h.accident_count,
                float(h.risk_score) if h.risk_score is not None else "",
                h.risk_level or "MODERATE",
                h.calculated_at.isoformat() if h.calculated_at else ""
            ]
            for h, zone_name in records
        ]
        return _generate_csv_response(f"Metrivon_hotspots_{timestamp_str}.csv", csv_headers, csv_rows)

    # =========================================================
    # 4. PREDICTIONS SAFETY SUMMARY REPORT
    # =========================================================
    elif rtype == "predictions":
        roads = db.query(Road).filter(Road.is_active == True).all()

        t_sub = (
            db.query(TrafficPrediction.start_road_id.label("road_id"), func.max(TrafficPrediction.created_at).label("max_ts"))
            .filter(TrafficPrediction.start_road_id.isnot(None))
            .group_by(TrafficPrediction.start_road_id)
            .subquery()
        )
        latest_traffic_preds = {
            tp.start_road_id: tp for tp in db.query(TrafficPrediction).join(
                t_sub, and_(TrafficPrediction.start_road_id == t_sub.c.road_id, TrafficPrediction.created_at == t_sub.c.max_ts)
            ).all()
        }

        a_sub = (
            db.query(AccidentPrediction.start_road_id.label("road_id"), func.max(AccidentPrediction.created_at).label("max_ts"))
            .filter(AccidentPrediction.start_road_id.isnot(None))
            .group_by(AccidentPrediction.start_road_id)
            .subquery()
        )
        latest_acc_preds = {
            ap.start_road_id: ap for ap in db.query(AccidentPrediction).join(
                a_sub, and_(AccidentPrediction.start_road_id == a_sub.c.road_id, AccidentPrediction.created_at == a_sub.c.max_ts)
            ).all()
        }

        results = []
        for r in roads:
            tp = latest_traffic_preds.get(r.road_id)
            ap = latest_acc_preds.get(r.road_id)
            results.append({
                "road_id": str(r.road_id),
                "road_name": r.road_name,
                "road_type": r.road_type,
                "speed_limit": float(r.speed_limit) if r.speed_limit else None,
                "predicted_congestion": tp.predicted_congestion if tp else "LOW",
                "predicted_vehicles": tp.predicted_vehicle_count if tp else None,
                "accident_risk_level": ap.risk_level if ap else "LOW",
                "accident_risk_pct": float(ap.risk_percentage) if ap else 20.0,
                "last_evaluated": (ap.created_at or tp.created_at or r.created_at).isoformat() if (ap or tp or r.created_at) else None
            })

        if fmt == "json":
            if paginated:
                start = (page - 1) * page_size
                return _page_envelope(results[start:start + page_size], len(results), page, page_size)
            return results

        csv_headers = [
            "Road ID",
            "Road Name",
            "Road Type",
            "Speed Limit (km/h)",
            "Predicted Congestion",
            "Predicted Vehicle Volume",
            "Accident Risk Level",
            "Accident Risk (%)",
            "Last Evaluated"
        ]
        csv_rows = [
            [
                item["road_id"],
                item["road_name"],
                item["road_type"],
                item["speed_limit"] or "",
                item["predicted_congestion"],
                item["predicted_vehicles"] or "",
                item["accident_risk_level"],
                f"{item['accident_risk_pct']:.1f}%",
                item["last_evaluated"] or ""
            ]
            for item in results
        ]
        return _generate_csv_response(f"Metrivon_predictions_{timestamp_str}.csv", csv_headers, csv_rows)

    # =========================================================
    # 5. SYSTEM-WIDE KPI SUMMARY REPORT
    # =========================================================
    elif rtype == "summary":
        total_roads = db.query(Road).count()
        active_roads = db.query(Road).filter(Road.is_active == True).count()
        total_accidents = db.query(Accident).count()
        fatal_accidents = db.query(Accident).filter(Accident.severity.ilike("FATAL")).count()
        severe_accidents = db.query(Accident).filter(Accident.severity.ilike("SEVERE")).count()
        total_traffic_records = db.query(TrafficRecord).count()
        total_hotspots = db.query(AccidentHotspot).count()

        summary_metrics = [
            {"metric": "Report Title", "value": "Metrivon AI System Operational Summary", "notes": "Generated by Traffic Analytics Engine"},
            {"metric": "Generated At (UTC)", "value": datetime.now(timezone.utc).isoformat(), "notes": f"Generated by {current_user.name} ({current_user.role.role_name if current_user.role else 'Authorized'})"},
            {"metric": "Total Registered Roads", "value": total_roads, "notes": "Monitored road network segments"},
            {"metric": "Active Monitored Roads", "value": active_roads, "notes": "Roads with live active telemetry"},
            {"metric": "Total Traffic Records", "value": total_traffic_records, "notes": "Cumulative traffic observation points"},
            {"metric": "Total Recorded Accidents", "value": total_accidents, "notes": "All historical accident incident records"},
            {"metric": "Fatal Incidents", "value": fatal_accidents, "notes": "Accidents with fatal classification"},
            {"metric": "Severe Incidents", "value": severe_accidents, "notes": "Accidents with severe injuries or structural damage"},
            {"metric": "Identified Hazard Hotspots", "value": total_hotspots, "notes": "Clusters flagged with elevated accident frequency"}
        ]

        if fmt == "json":
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": current_user.email,
                "summary": summary_metrics
            }

        csv_headers = ["Metric", "Value", "Description / Notes"]
        csv_rows = [[m["metric"], m["value"], m["notes"]] for m in summary_metrics]
        return _generate_csv_response(f"Metrivon_system_summary_{timestamp_str}.csv", csv_headers, csv_rows)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown report_type '{report_type}'. Supported types: 'accidents', 'traffic', 'hotspots', 'predictions', 'summary'."
        )
