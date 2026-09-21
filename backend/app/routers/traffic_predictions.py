from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    TrafficPrediction,
    Alert,
    AccidentPrediction
)
from app.schemas.prediction import (
    TrafficPredictionRunRequest,
    TrafficPredictionRunResponse,
    TrafficPredictionCreate,
    TrafficPredictionResponse,
    TrafficPipelineRunResponse,
    RoadRiskSummary,
    RoutePredictionRequest,
    RouteTrafficPredictionResponse
)
from app.ml.prediction_engine import (
    resolve_route_bundle,
    trigger_ml_traffic_model,
    trigger_ml_anomaly_model,
    format_estimated_time
)
from app.security import require_roles

router = APIRouter(
    tags=["AI Traffic Predictions"]
)


def _format_traffic_response(p: TrafficPrediction, road_name: Optional[str] = None) -> TrafficPredictionResponse:
    r_name = road_name or (p.road.road_name if p.road else None)
    target_dt = p.target_time or datetime.utcnow()
    est_time = format_estimated_time(target_dt)
    cong = p.predicted_congestion or "LOW"

    return TrafficPredictionResponse(
        prediction_id=p.prediction_id,
        road_id=p.road_id,
        road_name=r_name,
        prediction_time=p.prediction_time,
        target_time=target_dt,
        congestion_level=cong,
        estimated_time=est_time,
        predicted_congestion=cong,
        predicted_vehicle_count=p.predicted_vehicle_count,
        confidence_score=float(p.confidence_score) if p.confidence_score is not None else None,
        model_version_id=p.model_version_id,
        created_at=p.created_at
    )


# =========================================================
# 1. ROUTE-BASED TRAFFIC PREDICTION (START & END LOCATIONS)
# =========================================================

@router.post(
    "/predictions/traffic/route",
    response_model=RouteTrafficPredictionResponse,
    summary="Predict Traffic for User Start & End Locations"
)
def predict_route_traffic(
    req: RoutePredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Accepts Start and End locations (coordinates and/or location names) from frontend.
    The API fetches:
      - Start & End Latitude/Longitude
      - Road conditions (capacity, speed limit, lanes, condition)
      - Weather conditions from weather API / records (temperature, rainfall, visibility)
      - Previous traffic records (speed, density, volume)
    Then packages and triggers the ML model, returning:
      - congestion_level (LOW, MEDIUM, HIGH, SEVERE)
      - estimated_time (e.g. '4:00 PM - 5:00 PM (4pm to 5pm)')
      - the complete data bundle prepared for the ML model
    """
    now = datetime.now()
    target_time = req.target_time or (now + timedelta(minutes=req.target_minutes_ahead or 30))

    # 1. Resolve all required data for the ML model
    bundle = resolve_route_bundle(
        db=db,
        start_lat=req.start_latitude,
        start_lng=req.start_longitude,
        end_lat=req.end_latitude,
        end_lng=req.end_longitude,
        start_name=req.start_location,
        end_name=req.end_location,
        road_id=req.road_id,
        target_time=target_time
    )

    # 2. Trigger the ML model with the compiled feature bundle
    ml_result = trigger_ml_traffic_model(bundle)
    pred_record = None

    if req.persist and bundle["road"]:
        pred_record = TrafficPrediction(
            road_id=bundle["road"].road_id,
            prediction_time=now,
            target_time=target_time,
            predicted_congestion=ml_result["congestion_level"],
            predicted_vehicle_count=int(bundle["previous_records"]["vehicle_count"]),
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred_record)

        if ml_result["congestion_level"] == "SEVERE":
            alert = Alert(
                road_id=bundle["road"].road_id,
                prediction_id=pred_record.prediction_id,
                alert_type="PREDICTED_CONGESTION",
                severity="CRITICAL",
                message=f"Severe congestion predicted on {bundle['road'].road_name} for {ml_result['estimated_time']}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

        db.commit()
        db.refresh(pred_record)

    # 3. Evaluate Traffic Anomaly Detection in the same call
    anomaly_result = None
    try:
        anomaly_features = {
            "vehicle_count": float(bundle["previous_records"].get("vehicle_count") or 800),
            "average_speed": float(bundle["previous_records"].get("average_speed") or 35.0),
            "traffic_density": float(bundle["previous_records"].get("traffic_density") or 50.0),
            "road_capacity": float(bundle["road_conditions"].get("road_capacity") or 1500),
            "previous_traffic": float(bundle["previous_records"].get("previous_traffic") or bundle["previous_records"].get("vehicle_count") or 800),
            "hour": float(target_time.hour)
        }
        res_anom = trigger_ml_anomaly_model(anomaly_features)
        anomaly_result = {
            "prediction": res_anom.get("prediction", "NORMAL"),
            "is_anomaly": res_anom.get("is_anomaly", False),
            "anomaly_score": res_anom.get("anomaly_score", 0.0),
            "confidence_score": res_anom.get("confidence_score", 55.0),
            "model_status": res_anom.get("model_status", "trained-isolation-forest")
        }
    except Exception:
        anomaly_result = None

    return RouteTrafficPredictionResponse(
        prediction_id=pred_record.prediction_id if pred_record else None,
        road_id=bundle["road"].road_id if bundle["road"] else None,
        road_name=bundle["road_conditions"]["road_name"],
        start_location=bundle["start_label"],
        end_location=bundle["end_label"],
        start_latitude=bundle["start_latitude"],
        start_longitude=bundle["start_longitude"],
        end_latitude=bundle["end_latitude"],
        end_longitude=bundle["end_longitude"],
        distance_km=bundle["distance_km"],
        congestion_level=ml_result["congestion_level"],
        estimated_time=ml_result["estimated_time"],
        target_time=target_time,
        confidence_score=ml_result.get("confidence_score"),
        weather_conditions=bundle["weather_conditions"],
        road_conditions=bundle["road_conditions"],
        previous_records=bundle["previous_records"],
        route_geometry=bundle.get("route_geometry") or ml_result.get("route_geometry"),
        accident_points=ml_result.get("accident_points", []),
        anomaly_detection=anomaly_result,
        live_traffic=bundle.get("live_traffic") or ml_result.get("live_traffic"),
        ml_features=bundle["ml_features"],
        ml_source=ml_result.get("ml_source", "backend-feature-engine"),
        created_at=now
    )


# =========================================================
# 2. RUN TRAFFIC PREDICTION MODEL (SINGLE ROAD ON-DEMAND)
# =========================================================

@router.post(
    "/predictions/traffic/predict",
    response_model=TrafficPredictionRunResponse,
    summary="Run Traffic Congestion Prediction Model"
)
def run_traffic_prediction(
    req: TrafficPredictionRunRequest,
    db: Session = Depends(get_db)
):
    """
    Executes the ML model for traffic congestion prediction on a specific road.
    Returns:
      - congestion_level (LOW, MEDIUM, HIGH, SEVERE)
      - estimated_time window (e.g. '4:00 PM - 5:00 PM (4pm to 5pm)')
    """
    road = db.query(Road).filter(Road.road_id == req.road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot predict traffic: Road with ID '{req.road_id}' does not exist."
        )

    now = datetime.now()
    target_time = req.target_time or (now + timedelta(minutes=req.target_minutes_ahead or 30))

    bundle = resolve_route_bundle(
        db=db,
        road_id=road.road_id,
        target_time=target_time
    )

    # Apply any request overrides if provided by caller / ML people
    if req.predicted_congestion:
        ml_result = {
            "congestion_level": req.predicted_congestion.upper(),
            "estimated_time": format_estimated_time(target_time),
            "confidence_score": req.confidence_score if req.confidence_score is not None else None,
            "ml_source": "caller-override"
        }
    else:
        ml_result = trigger_ml_traffic_model(bundle)

    pred_record = None
    if req.persist:
        pred_record = TrafficPrediction(
            road_id=req.road_id,
            prediction_time=now,
            target_time=target_time,
            predicted_congestion=ml_result["congestion_level"],
            predicted_vehicle_count=int(req.predicted_vehicle_count if req.predicted_vehicle_count is not None else bundle["previous_records"]["vehicle_count"]),
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred_record)

        if ml_result["congestion_level"] == "SEVERE":
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred_record.prediction_id,
                alert_type="PREDICTED_CONGESTION",
                severity="CRITICAL",
                message=f"Severe congestion predicted on {road.road_name} for {ml_result['estimated_time']}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

        db.commit()
        db.refresh(pred_record)

    # Evaluate Anomaly Detection in the same call
    anomaly_result = None
    try:
        anomaly_features = {
            "vehicle_count": float(req.predicted_vehicle_count if req.predicted_vehicle_count is not None else bundle["previous_records"]["vehicle_count"]),
            "average_speed": float(bundle["previous_records"].get("average_speed") or 35.0),
            "traffic_density": float(bundle["previous_records"].get("traffic_density") or 50.0),
            "road_capacity": float(bundle["road_conditions"].get("road_capacity") or 1500),
            "previous_traffic": float(bundle["previous_records"].get("previous_traffic") or bundle["previous_records"].get("vehicle_count") or 800),
            "hour": float(target_time.hour)
        }
        res_anom = trigger_ml_anomaly_model(anomaly_features)
        anomaly_result = {
            "prediction": res_anom.get("prediction", "NORMAL"),
            "is_anomaly": res_anom.get("is_anomaly", False),
            "anomaly_score": res_anom.get("anomaly_score", 0.0),
            "confidence_score": res_anom.get("confidence_score", 55.0),
            "model_status": res_anom.get("model_status", "trained-isolation-forest")
        }
    except Exception:
        anomaly_result = None

    return TrafficPredictionRunResponse(
        prediction_id=pred_record.prediction_id if pred_record else None,
        road_id=road.road_id,
        road_name=road.road_name,
        congestion_level=ml_result["congestion_level"],
        estimated_time=ml_result["estimated_time"],
        target_time=target_time,
        predicted_congestion=ml_result["congestion_level"],
        predicted_vehicle_count=int(req.predicted_vehicle_count if req.predicted_vehicle_count is not None else bundle["previous_records"]["vehicle_count"]),
        confidence_score=ml_result.get("confidence_score"),
        class_probabilities={ml_result["congestion_level"]: ml_result.get("confidence_score")},
        anomaly_detection=anomaly_result,
        created_at=now
    )


# =========================================================
# 3. INGESTION & PIPELINE APIS (FOR ML TEAM PIPELINES)
# =========================================================

@router.post(
    "/predictions/traffic",
    response_model=TrafficPredictionResponse,
    summary="Ingest Traffic Congestion Prediction (ML Pipeline)",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def store_traffic_prediction(
    pred_in: TrafficPredictionCreate,
    db: Session = Depends(get_db)
):
    road = db.query(Road).filter(Road.road_id == pred_in.road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot record prediction: Road with ID '{pred_in.road_id}' does not exist."
        )

    now = datetime.now()
    cong = pred_in.predicted_congestion.upper()

    pred = TrafficPrediction(
        road_id=pred_in.road_id,
        prediction_time=now,
        target_time=pred_in.target_time,
        predicted_congestion=cong,
        predicted_vehicle_count=pred_in.predicted_vehicle_count,
        confidence_score=pred_in.confidence_score,
        model_version_id=pred_in.model_version_id,
        created_at=now
    )
    db.add(pred)

    if cong == "SEVERE":
        est_time = format_estimated_time(pred_in.target_time)
        alert = Alert(
            road_id=road.road_id,
            prediction_id=pred.prediction_id,
            alert_type="PREDICTED_CONGESTION",
            severity="CRITICAL",
            message=f"Severe congestion predicted on {road.road_name} for {est_time}.",
            status="ACTIVE",
            created_at=now
        )
        db.add(alert)

    db.commit()
    db.refresh(pred)

    return _format_traffic_response(pred, road.road_name)


@router.post(
    "/ai/traffic/run-pipeline",
    response_model=TrafficPipelineRunResponse,
    summary="Run Traffic Congestion Pipeline across All Active Roads",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def run_traffic_pipeline(
    db: Session = Depends(get_db)
):
    roads = db.query(Road).filter(Road.is_active == True).all()
    now = datetime.now()
    target_time = now + timedelta(minutes=30)

    predictions_count = 0
    alerts_count = 0

    for road in roads:
        bundle = resolve_route_bundle(db=db, road_id=road.road_id, target_time=target_time)
        ml_result = trigger_ml_traffic_model(bundle)

        pred = TrafficPrediction(
            road_id=road.road_id,
            prediction_time=now,
            target_time=target_time,
            predicted_congestion=ml_result["congestion_level"],
            predicted_vehicle_count=int(bundle["previous_records"]["vehicle_count"]),
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred)
        predictions_count += 1

        if ml_result["congestion_level"] == "SEVERE":
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred.prediction_id,
                alert_type="PREDICTED_CONGESTION",
                severity="CRITICAL",
                message=f"Severe congestion predicted on {road.road_name} for {ml_result['estimated_time']}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)
            alerts_count += 1

    db.commit()

    return TrafficPipelineRunResponse(
        status="SUCCESS",
        scanned_roads=len(roads),
        predictions_generated=predictions_count,
        severe_alerts_raised=alerts_count,
        timestamp=now
    )


# =========================================================
# 4. QUERY ENDPOINTS (LATEST & ROAD HISTORY)
# =========================================================

@router.get(
    "/predictions/traffic/latest",
    response_model=List[TrafficPredictionResponse],
    summary="Get Latest Traffic Predictions Across Roads"
)
def get_latest_traffic_predictions(
    db: Session = Depends(get_db)
):
    subquery = (
        db.query(
            TrafficPrediction.road_id,
            func.max(TrafficPrediction.created_at).label("max_created")
        )
        .group_by(TrafficPrediction.road_id)
        .subquery()
    )

    records = (
        db.query(TrafficPrediction, Road.road_name)
        .join(
            subquery,
            and_(
                TrafficPrediction.road_id == subquery.c.road_id,
                TrafficPrediction.created_at == subquery.c.max_created
            )
        )
        .join(Road, TrafficPrediction.road_id == Road.road_id)
        .order_by(TrafficPrediction.target_time.asc())
        .all()
    )

    return [_format_traffic_response(p, road_name) for p, road_name in records]


@router.get(
    "/predictions/traffic/road/{road_id}",
    response_model=List[TrafficPredictionResponse],
    summary="Get Traffic Predictions Timeline for a Specific Road"
)
def get_road_traffic_predictions(
    road_id: UUID,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    road = db.query(Road).filter(Road.road_id == road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Road with ID '{road_id}' does not exist."
        )

    records = (
        db.query(TrafficPrediction)
        .filter(TrafficPrediction.road_id == road_id)
        .order_by(TrafficPrediction.target_time.desc())
        .limit(limit)
        .all()
    )

    return [_format_traffic_response(p, road.road_name) for p in records]


# =========================================================
# 5. INTEGRATED SUMMARY (FOR DASHBOARD & LIVE MAP)
# =========================================================

@router.get(
    "/predictions/summary",
    response_model=List[RoadRiskSummary],
    summary="Integrated Road Prediction & Safety Summary"
)
def get_prediction_summary(
    db: Session = Depends(get_db)
):
    roads = db.query(Road).filter(Road.is_active == True).all()

    t_sub = (
        db.query(TrafficPrediction.road_id, func.max(TrafficPrediction.created_at).label("max_ts"))
        .group_by(TrafficPrediction.road_id)
        .subquery()
    )
    latest_traffic_preds = {
        tp.road_id: tp for tp in db.query(TrafficPrediction).join(
            t_sub, and_(TrafficPrediction.road_id == t_sub.c.road_id, TrafficPrediction.created_at == t_sub.c.max_ts)
        ).all()
    }

    a_sub = (
        db.query(AccidentPrediction.road_id, func.max(AccidentPrediction.created_at).label("max_ts"))
        .group_by(AccidentPrediction.road_id)
        .subquery()
    )
    latest_acc_preds = {
        ap.road_id: ap for ap in db.query(AccidentPrediction).join(
            a_sub, and_(AccidentPrediction.road_id == a_sub.c.road_id, AccidentPrediction.created_at == a_sub.c.max_ts)
        ).all()
    }

    results = []
    for road in roads:
        tp = latest_traffic_preds.get(road.road_id)
        ap = latest_acc_preds.get(road.road_id)

        cong = tp.predicted_congestion if tp else "LOW"
        risk_lvl = ap.risk_level if ap else "LOW"
        risk_pct = float(ap.risk_percentage) if ap else 20.0

        if risk_lvl in ["CRITICAL", "HIGH"] or cong == "SEVERE":
            color = "#EF4444"  # Red
        elif risk_lvl == "MEDIUM" or cong == "HIGH":
            color = "#F59E0B"  # Amber/Yellow
        else:
            color = "#10B981"  # Green

        last_updated = ap.created_at if ap else (tp.created_at if tp else road.created_at)

        results.append(RoadRiskSummary(
            road_id=road.road_id,
            road_name=road.road_name,
            latest_predicted_congestion=cong,
            latest_accident_risk_level=risk_lvl,
            risk_percentage=risk_pct,
            color=color,
            last_updated=last_updated
        ))

    return results
