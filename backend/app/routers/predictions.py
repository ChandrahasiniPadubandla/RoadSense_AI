from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database.connection import get_db
from app.database.models import (
    Road,
    TrafficRecord,
    Accident,
    TrafficPrediction,
    AccidentPrediction,
    Alert,
    WeatherRecord
)
from app.schemas.prediction import (
    TrafficPredictionCreate,
    TrafficPredictionResponse,
    AccidentPredictionCreate,
    AccidentPredictionResponse,
    RoadRiskSummary
)


router = APIRouter(
    prefix="/api/predictions",
    tags=["AI Predictions (Traffic & Accidents)"]
)



def _format_traffic_prediction(p: TrafficPrediction, road_name: Optional[str] = None) -> TrafficPredictionResponse:
    r_name = road_name or (p.road.road_name if p.road else None)
    return TrafficPredictionResponse(
        prediction_id=p.prediction_id,
        road_id=p.road_id,
        road_name=r_name,
        prediction_time=p.prediction_time,
        target_time=p.target_time,
        predicted_congestion=p.predicted_congestion,
        predicted_vehicle_count=p.predicted_vehicle_count,
        confidence_score=float(p.confidence_score) if p.confidence_score is not None else None,
        model_version_id=p.model_version_id,
        created_at=p.created_at
    )


def _format_accident_prediction(p: AccidentPrediction, road_name: Optional[str] = None) -> AccidentPredictionResponse:
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
# TRAFFIC CONGESTION PREDICTION ENDPOINTS (Module 3)
# =========================================================

@router.post(
    "/traffic",
    response_model=TrafficPredictionResponse,
    summary="Ingest an ML Traffic Prediction"
)
def store_traffic_prediction(
    pred_in: TrafficPredictionCreate,
    db: Session = Depends(get_db)
):
    """
    Stores an ML model predicted traffic congestion record into `traffic_predictions`.
    Automatically raises an active system alert if SEVERE congestion is predicted.
    """
    road = db.query(Road).filter(Road.road_id == pred_in.road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot record prediction: Road with ID '{pred_in.road_id}' does not exist. Please check the road ID."
        )

    now = datetime.utcnow()
    pred = TrafficPrediction(
        road_id=pred_in.road_id,
        prediction_time=now,
        target_time=pred_in.target_time,
        predicted_congestion=pred_in.predicted_congestion.upper(),
        predicted_vehicle_count=pred_in.predicted_vehicle_count,
        confidence_score=pred_in.confidence_score,
        model_version_id=pred_in.model_version_id,
        created_at=now
    )
    db.add(pred)

    # Auto-generate alert if severe congestion is predicted
    if pred_in.predicted_congestion.upper() == "SEVERE":
        existing_alert = (
            db.query(Alert)
            .filter(
                Alert.road_id == road.road_id,
                Alert.alert_type == "PREDICTED_CONGESTION",
                Alert.status == "ACTIVE"
            )
            .first()
        )
        if not existing_alert:
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred.prediction_id,
                alert_type="PREDICTED_CONGESTION",
                severity="CRITICAL",
                message=f"Severe congestion predicted on {road.road_name} at {pred_in.target_time.strftime('%H:%M')} with {pred_in.predicted_vehicle_count or 'heavy'} vehicles.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

    db.commit()
    db.refresh(pred)

    return _format_traffic_prediction(pred, road.road_name)


@router.get(
    "/traffic/latest",
    response_model=list[TrafficPredictionResponse],
    summary="Get Latest Traffic Predictions Across Monitored Roads"
)
def get_latest_traffic_predictions(
    db: Session = Depends(get_db)
):
    """
    Returns the most recent predicted congestion status for each road.
    """
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

    return [_format_traffic_prediction(p, road_name) for p, road_name in records]


@router.get(
    "/traffic/road/{road_id}",
    response_model=list[TrafficPredictionResponse],
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
            detail=f"Road with ID '{road_id}' does not exist. Cannot retrieve traffic predictions."
        )

    records = (
        db.query(TrafficPrediction)
        .filter(TrafficPrediction.road_id == road_id)
        .order_by(TrafficPrediction.target_time.desc())
        .limit(limit)
        .all()
    )

    return [_format_traffic_prediction(p, road.road_name) for p in records]






# =========================================================
# ACCIDENT RISK PREDICTION ENDPOINTS (Module 5)
# =========================================================

@router.post(
    "/accidents",
    response_model=AccidentPredictionResponse,
    summary="Ingest an ML Accident Risk Prediction"
)
def store_accident_prediction(
    pred_in: AccidentPredictionCreate,
    db: Session = Depends(get_db)
):
    """
    Stores an ML model predicted accident risk percentage into `accident_predictions`.
    Automatically raises an active accident hazard alert if risk level is HIGH or CRITICAL.
    """
    road = db.query(Road).filter(Road.road_id == pred_in.road_id).first()
    if not road:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot record accident prediction: Road with ID '{pred_in.road_id}' does not exist. Please check the road ID."
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

    # Auto-generate alert if high/critical accident risk is predicted
    if risk_level in ["HIGH", "CRITICAL"]:
        existing_alert = (
            db.query(Alert)
            .filter(
                Alert.road_id == road.road_id,
                Alert.alert_type == "ACCIDENT_RISK_WARNING",
                Alert.status == "ACTIVE"
            )
            .first()
        )
        if not existing_alert:
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

    return _format_accident_prediction(pred, road.road_name)


@router.get(
    "/accidents/latest",
    response_model=list[AccidentPredictionResponse],
    summary="Get Latest Accident Risk Predictions Across Monitored Roads"
)
def get_latest_accident_predictions(
    db: Session = Depends(get_db)
):
    """
    Returns the most recent predicted accident risk percentage and level for each road.
    """
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

    return [_format_accident_prediction(p, road_name) for p, road_name in records]


@router.get(
    "/accidents/road/{road_id}",
    response_model=list[AccidentPredictionResponse],
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
            detail=f"Road with ID '{road_id}' does not exist. Cannot retrieve accident predictions."
        )

    records = (
        db.query(AccidentPrediction)
        .filter(AccidentPrediction.road_id == road_id)
        .order_by(AccidentPrediction.prediction_time.desc())
        .limit(limit)
        .all()
    )

    return [_format_accident_prediction(p, road.road_name) for p in records]





# =========================================================
# INTEGRATED DASHBOARD PREDICTION SUMMARY & BATCH PIPELINE RUN
# =========================================================

@router.get(
    "/summary",
    response_model=list[RoadRiskSummary],
    summary="Integrated Road Prediction & Safety Summary"
)
def get_prediction_summary(
    db: Session = Depends(get_db)
):
    """
    Returns integrated traffic congestion and accident risk summary
    with styled map color for each active road segment.
    """
    roads = db.query(Road).filter(Road.is_active == True).all()

    # Get latest traffic predictions
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

    # Get latest accident predictions
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

        # Styling color logic
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
