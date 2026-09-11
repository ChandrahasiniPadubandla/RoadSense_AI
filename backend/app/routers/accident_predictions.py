from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database.connection import get_db
from app.database.models import (
    Road,
    Accident,
    AccidentPrediction,
    Alert,
    TrafficRecord
)
from app.schemas.prediction import (
    AccidentPredictionRunRequest,
    AccidentPredictionRunResponse,
    AccidentPredictionCreate,
    AccidentPredictionResponse,
    AccidentPipelineRunResponse,
    RoutePredictionRequest,
    RouteAccidentPredictionResponse
)
from app.ml.prediction_engine import (
    resolve_route_bundle,
    trigger_ml_accident_model
)

router = APIRouter(
    tags=["AI Accident Predictions"]
)


def _format_accident_response(p: AccidentPrediction, road_name: Optional[str] = None) -> AccidentPredictionResponse:
    r_name = road_name or (p.road.road_name if p.road else None)
    return AccidentPredictionResponse(
        prediction_id=p.prediction_id,
        road_id=p.road_id,
        road_name=r_name,
        prediction_time=p.prediction_time,
        risk_percentage=float(p.risk_percentage),
        risk_level=p.risk_level,
        confidence_score=float(p.confidence_score) if p.confidence_score is not None else None,
        model_version_id=p.model_version_id,
        created_at=p.created_at
    )


# =========================================================
# 1. ROUTE-BASED ACCIDENT PREDICTION (START & END LOCATIONS)
# =========================================================

@router.post(
    "/api/predictions/accidents/route",
    response_model=RouteAccidentPredictionResponse,
    summary="Predict Accident Risk for User Start & End Locations"
)
def predict_route_accident(
    req: RoutePredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Accepts Start and End locations (coordinates and/or location names) from frontend.
    The API fetches:
      - Start & End Latitude/Longitude
      - Road conditions (capacity, speed limit, lanes, road condition)
      - Weather conditions from weather API / records (temperature, rainfall, visibility)
      - Previous traffic records (speed, density, volume)
      - Historical accident frequency along this corridor
    Then packages and triggers the ML model, returning:
      - risk_percentage (0.0 - 100.0%)
      - categorical risk_level (LOW, MEDIUM, HIGH, CRITICAL)
      - the complete data bundle prepared for the ML model
    """
    now = datetime.utcnow()
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
    ml_result = trigger_ml_accident_model(bundle)
    pred_record = None

    if req.persist and bundle["road"]:
        pred_record = AccidentPrediction(
            road_id=bundle["road"].road_id,
            prediction_time=now,
            risk_percentage=ml_result["risk_percentage"],
            risk_level=ml_result["risk_level"],
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred_record)

        if ml_result["risk_level"] in ["HIGH", "CRITICAL"]:
            alert = Alert(
                road_id=bundle["road"].road_id,
                prediction_id=pred_record.prediction_id,
                alert_type="ACCIDENT_RISK_WARNING",
                severity="CRITICAL" if ml_result["risk_level"] == "CRITICAL" else "HIGH",
                message=f"Elevated accident risk ({ml_result['risk_percentage']}% - {ml_result['risk_level']}) predicted between {bundle['start_label']} and {bundle['end_label']}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

        db.commit()
        db.refresh(pred_record)

    return RouteAccidentPredictionResponse(
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
        risk_percentage=ml_result["risk_percentage"],
        risk_level=ml_result["risk_level"],
        confidence_score=ml_result.get("confidence_score"),
        prediction_time=now,
        weather_conditions=bundle["weather_conditions"],
        road_conditions=bundle["road_conditions"],
        previous_records=bundle["previous_records"],
        historical_accidents_count=bundle["historical_accidents_count"],
        ml_features=bundle["ml_features"],
        ml_source=ml_result.get("ml_source", "backend-feature-engine"),
        created_at=now
    )


# =========================================================
# 2. RUN ACCIDENT PREDICTION MODEL (SINGLE ROAD ON-DEMAND)
# =========================================================

@router.post(
    "/api/predictions/accidents/predict",
    response_model=AccidentPredictionRunResponse,
    summary="Run Accident Risk Prediction Model"
)
def run_accident_prediction(
    req: AccidentPredictionRunRequest,
    db: Session = Depends(get_db)
):
    """
    Executes the ML model for accident risk prediction on a specific road.
    Returns:
      - risk_percentage (e.g. 45.8%)
      - categorical risk_level (LOW, MEDIUM, HIGH, CRITICAL)
    """
    road = db.query(Road).filter(Road.road_id == req.road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot predict accident risk: Road with ID '{req.road_id}' does not exist."
        )

    now = datetime.utcnow()
    bundle = resolve_route_bundle(db=db, road_id=road.road_id)

    # Apply any overrides from caller / ML team
    if req.risk_percentage is not None:
        risk_pct = float(req.risk_percentage)
        risk_lvl = req.risk_level or ("CRITICAL" if risk_pct >= 70 else ("HIGH" if risk_pct >= 50 else ("MEDIUM" if risk_pct >= 30 else "LOW")))
        ml_result = {
            "risk_percentage": round(risk_pct, 1),
            "risk_level": risk_lvl.upper(),
            "confidence_score": req.confidence_score or 90.0,
            "ml_source": "caller-override"
        }
    else:
        ml_result = trigger_ml_accident_model(bundle)

    pred_record = None
    if req.persist:
        pred_record = AccidentPrediction(
            road_id=req.road_id,
            prediction_time=now,
            risk_percentage=ml_result["risk_percentage"],
            risk_level=ml_result["risk_level"],
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred_record)

        if ml_result["risk_level"] in ["HIGH", "CRITICAL"]:
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred_record.prediction_id,
                alert_type="ACCIDENT_RISK_WARNING",
                severity="CRITICAL" if ml_result["risk_level"] == "CRITICAL" else "HIGH",
                message=f"Elevated accident risk ({ml_result['risk_percentage']}% - {ml_result['risk_level']}) predicted on {road.road_name}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

        db.commit()
        db.refresh(pred_record)

    return AccidentPredictionRunResponse(
        prediction_id=pred_record.prediction_id if pred_record else None,
        road_id=road.road_id,
        road_name=road.road_name,
        risk_percentage=ml_result["risk_percentage"],
        risk_level=ml_result["risk_level"],
        confidence_score=ml_result.get("confidence_score"),
        prediction_time=now,
        created_at=now
    )


# =========================================================
# 3. INGESTION & PIPELINE APIS (FOR ML TEAM PIPELINES)
# =========================================================

@router.post(
    "/api/predictions/accidents",
    response_model=AccidentPredictionResponse,
    summary="Ingest Accident Risk Prediction (ML Pipeline)"
)
def store_accident_prediction(
    pred_in: AccidentPredictionCreate,
    db: Session = Depends(get_db)
):
    road = db.query(Road).filter(Road.road_id == pred_in.road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot record accident prediction: Road with ID '{pred_in.road_id}' does not exist."
        )

    now = datetime.utcnow()
    risk_level = pred_in.risk_level.upper()

    pred = AccidentPrediction(
        road_id=pred_in.road_id,
        prediction_time=now,
        risk_percentage=pred_in.risk_percentage,
        risk_level=risk_level,
        confidence_score=pred_in.confidence_score,
        model_version_id=pred_in.model_version_id,
        created_at=now
    )
    db.add(pred)

    if risk_level in ["HIGH", "CRITICAL"]:
        alert = Alert(
            road_id=road.road_id,
            prediction_id=pred.prediction_id,
            alert_type="ACCIDENT_RISK_WARNING",
            severity="CRITICAL" if risk_level == "CRITICAL" else "HIGH",
            message=f"Elevated accident risk ({pred_in.risk_percentage:.1f}% - {risk_level}) predicted on {road.road_name}.",
            status="ACTIVE",
            created_at=now
        )
        db.add(alert)

    db.commit()
    db.refresh(pred)

    return _format_accident_response(pred, road.road_name)


@router.post(
    "/api/ai/accidents/run-pipeline",
    response_model=AccidentPipelineRunResponse,
    summary="Run Accident Risk Pipeline across All Active Roads"
)
def run_accident_pipeline(
    db: Session = Depends(get_db)
):
    roads = db.query(Road).filter(Road.is_active == True).all()
    now = datetime.utcnow()

    predictions_count = 0
    alerts_count = 0

    for road in roads:
        bundle = resolve_route_bundle(db=db, road_id=road.road_id)
        ml_result = trigger_ml_accident_model(bundle)

        pred = AccidentPrediction(
            road_id=road.road_id,
            prediction_time=now,
            risk_percentage=ml_result["risk_percentage"],
            risk_level=ml_result["risk_level"],
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred)
        predictions_count += 1

        if ml_result["risk_level"] in ["HIGH", "CRITICAL"]:
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred.prediction_id,
                alert_type="ACCIDENT_RISK_WARNING",
                severity="CRITICAL" if ml_result["risk_level"] == "CRITICAL" else "HIGH",
                message=f"Elevated accident risk ({ml_result['risk_percentage']}% - {ml_result['risk_level']}) predicted on {road.road_name}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)
            alerts_count += 1

    db.commit()

    return AccidentPipelineRunResponse(
        status="SUCCESS",
        scanned_roads=len(roads),
        predictions_generated=predictions_count,
        critical_alerts_raised=alerts_count,
        timestamp=now
    )


# =========================================================
# 4. QUERY ENDPOINTS (LATEST & ROAD HISTORY)
# =========================================================

@router.get(
    "/api/predictions/accidents/latest",
    response_model=List[AccidentPredictionResponse],
    summary="Get Latest Accident Risk Predictions Across Roads"
)
def get_latest_accident_predictions(
    db: Session = Depends(get_db)
):
    subquery = (
        db.query(
            AccidentPrediction.road_id,
            func.max(AccidentPrediction.created_at).label("max_created")
        )
        .group_by(AccidentPrediction.road_id)
        .subquery()
    )

    records = (
        db.query(AccidentPrediction, Road.road_name)
        .join(
            subquery,
            and_(
                AccidentPrediction.road_id == subquery.c.road_id,
                AccidentPrediction.created_at == subquery.c.max_created
            )
        )
        .join(Road, AccidentPrediction.road_id == Road.road_id)
        .order_by(AccidentPrediction.risk_percentage.desc())
        .all()
    )

    return [_format_accident_response(p, road_name) for p, road_name in records]


@router.get(
    "/api/predictions/accidents/road/{road_id}",
    response_model=List[AccidentPredictionResponse],
    summary="Get Accident Risk History for a Specific Road"
)
def get_road_accident_predictions(
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
        db.query(AccidentPrediction)
        .filter(AccidentPrediction.road_id == road_id)
        .order_by(AccidentPrediction.prediction_time.desc())
        .limit(limit)
        .all()
    )

    return [_format_accident_response(p, road.road_name) for p in records]
