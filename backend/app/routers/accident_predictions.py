import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from geoalchemy2.shape import to_shape

from app.database.connection import get_db
from app.database.models import (
    Road,
    Accident,
    AccidentPrediction,
    Alert,
    TrafficZone,
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
from app.schemas.accident_risk import (
    AccidentRiskPredictionRequest,
    AccidentRiskPredictionResponse,
)
from app.services.accident_risk_service import accident_risk_service
from app.services.accident_risk_feature_service import accident_risk_feature_service
from app.ml.prediction_engine import (
    resolve_route_bundle,
    trigger_ml_accident_model
)
from app.security import require_roles
from app.services.hotspot_service import upsert_accident_hotspot
from app.services.geocoding import get_or_create_road_from_geocoding

router = APIRouter(
    tags=["AI Accident Predictions"]
)


@router.post(
    "/accident-predictions/predict",
    response_model=AccidentRiskPredictionResponse,
    summary="Predict accident risk for a real road using database-derived features"
)
def predict_accident_risk_route(
    req: AccidentRiskPredictionRequest,
    db: Session = Depends(get_db),
):
    created_new_road = False
    road = None
    if req.road_id is not None:
        road = db.query(Road).filter(Road.road_id == req.road_id).first()
    if road is None and req.road_name:
        road, created_new_road = get_or_create_road_from_geocoding(db=db, road_name=req.road_name)

    if road is None:
        identifier = str(req.road_id) if req.road_id else req.road_name
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "ROAD_NOT_FOUND",
                "message": f"Road '{identifier}' does not exist in the database and could not be geocoded.",
                "field": "road_id" if req.road_id else "road_name",
            },
        )

    try:
        feature_payload = accident_risk_feature_service.build_feature_payload(db, road.road_id)
        result = accident_risk_service.predict(feature_payload)
    except ValueError as exc:
        logger = logging.getLogger("Metrivon")
        logger.exception("Accident-risk feature preparation failed for road_id=%s", road.road_id)
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "MISSING_PREDICTION_DATA",
                "message": str(exc),
                "field": "road_id",
            },
        ) from exc
    except RuntimeError as exc:
        logger = logging.getLogger("Metrivon")
        logger.exception("Accident-risk prediction failed for road_id=%s", road.road_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "MODEL_PREDICTION_FAILED",
                "message": "Accident-risk prediction failed during inference.",
            },
        ) from exc

    if result.get("accident_risk_level") in ["HIGH", "SEVERE", "CRITICAL"]:
        h_lat, h_lng = None, None
        if road.start_location is not None:
            try:
                pt = to_shape(road.start_location)
                h_lat, h_lng = float(pt.y), float(pt.x)
            except Exception:
                pass
        elif road.zone_id:
            zone = db.query(TrafficZone).filter(TrafficZone.zone_id == road.zone_id).first()
            if zone and zone.location is not None:
                try:
                    pt = to_shape(zone.location)
                    h_lat, h_lng = float(pt.y), float(pt.x)
                except Exception:
                    pass

        real_acc_count = db.query(Accident).filter(Accident.road_id == road.road_id).count()

        upsert_accident_hotspot(
            db=db,
            latitude=h_lat,
            longitude=h_lng,
            risk_level=result["accident_risk_level"],
            risk_score=float(result.get("accident_risk") or 0.0),
            accident_count=real_acc_count,
            zone_id=road.zone_id,
            calculated_at=datetime.utcnow()
        )
        db.commit()

    return AccidentRiskPredictionResponse(
        success=True,
        road_id=road.road_id,
        road_name=road.road_name,
        accident_risk=result["accident_risk"],
        accident_risk_level=result["accident_risk_level"],
        created_new_road=created_new_road,
        model_status="loaded",
    )


def _format_accident_response(p: AccidentPrediction, road_name: Optional[str] = None) -> AccidentPredictionResponse:
    if p.start_location and p.end_location:
        r_name = f"{p.start_location} → {p.end_location}"
    elif road_name:
        r_name = road_name
    elif p.start_road and p.start_road.road_name:
        r_name = p.start_road.road_name
    elif p.end_road and p.end_road.road_name:
        r_name = p.end_road.road_name
    else:
        r_name = p.start_location or p.end_location or "Route Segment"

    return AccidentPredictionResponse(
        prediction_id=p.prediction_id,
        start_road_id=p.start_road_id,
        end_road_id=p.end_road_id,
        start_location=p.start_location,
        end_location=p.end_location,
        distance_km=float(p.distance_km) if p.distance_km is not None else None,
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
    "/predictions/accidents/route",
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
    now = datetime.now()
    target_time = req.target_time or (now + timedelta(minutes=req.target_minutes_ahead or 30))
    if target_time.tzinfo is not None:
        target_time = target_time.astimezone().replace(tzinfo=None)

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

    if req.persist:
        pred_record = AccidentPrediction(
            start_road_id=bundle.get("start_road_id"),
            end_road_id=bundle.get("end_road_id"),
            start_location=bundle.get("start_label"),
            end_location=bundle.get("end_label"),
            distance_km=bundle.get("distance_km"),
            prediction_time=now,
            risk_percentage=ml_result["risk_percentage"],
            risk_level=ml_result["risk_level"],
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred_record)

        alert_road_id = bundle.get("start_road_id") or bundle.get("end_road_id")
        if ml_result["risk_level"] in ["HIGH", "SEVERE", "CRITICAL"] and alert_road_id:
            alert = Alert(
                road_id=alert_road_id,
                prediction_id=pred_record.prediction_id,
                alert_type="ACCIDENT_RISK_WARNING",
                severity="CRITICAL" if ml_result["risk_level"] in ["CRITICAL", "SEVERE"] else "HIGH",
                message=f"Elevated accident risk ({ml_result['risk_percentage']}% - {ml_result['risk_level']}) predicted between {bundle['start_label']} and {bundle['end_label']}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

        # Persist / update AccidentHotspot in DB
        if ml_result["risk_level"] in ["HIGH", "SEVERE", "CRITICAL"] or float(ml_result["risk_percentage"]) >= 50.0:
            coords = bundle.get("route_geometry")
            if coords and len(coords) >= 2:
                mid_idx = len(coords) // 2
                h_lat, h_lng = coords[mid_idx]
            else:
                h_lat = (float(bundle["start_latitude"]) + float(bundle["end_latitude"])) / 2.0
                h_lng = (float(bundle["start_longitude"]) + float(bundle["end_longitude"])) / 2.0

            upsert_accident_hotspot(
                db=db,
                latitude=float(h_lat),
                longitude=float(h_lng),
                risk_level=ml_result["risk_level"],
                risk_score=float(ml_result["risk_percentage"]),
                accident_count=int(bundle.get("historical_accidents_count") or 1),
                zone_id=bundle["road"].zone_id if bundle.get("road") else None,
                calculated_at=now
            )

        db.commit()
        db.refresh(pred_record)

    return RouteAccidentPredictionResponse(
        prediction_id=pred_record.prediction_id if pred_record else None,
        start_road_id=bundle.get("start_road_id"),
        end_road_id=bundle.get("end_road_id"),
        road_name=bundle["road_conditions"]["road_name"],
        created_new_road=bundle.get("created_new_road", False),
        newly_created_roads=bundle.get("newly_created_roads", []),
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
        route_geometry=bundle.get("route_geometry") or ml_result.get("route_geometry"),
        accident_points=ml_result.get("accident_points", []),
        ml_features=bundle["ml_features"],
        ml_source=ml_result.get("ml_source", "backend-feature-engine"),
        created_at=now
    )


# =========================================================
# 2. RUN ACCIDENT PREDICTION MODEL (SINGLE ROAD ON-DEMAND)
# =========================================================

@router.post(
    "/predictions/accidents/predict",
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
    road = None
    created_new_road = False
    if req.road_id is not None:
        road = db.query(Road).filter(Road.road_id == req.road_id).first()
    if road is None and req.road_name:
        road, created_new_road = get_or_create_road_from_geocoding(db=db, road_name=req.road_name)

    if not road:
        identifier = str(req.road_id) if req.road_id else req.road_name
        raise HTTPException(
            status_code=404,
            detail=f"Cannot predict accident risk: Road '{identifier}' does not exist and could not be geocoded."
        )

    now = datetime.now()
    bundle = resolve_route_bundle(db=db, road_id=road.road_id)

    # Apply any overrides from caller / ML team
    if req.risk_percentage is not None:
        risk_pct = float(req.risk_percentage)
        risk_lvl = req.risk_level or ("CRITICAL" if risk_pct >= 70 else ("HIGH" if risk_pct >= 50 else ("MEDIUM" if risk_pct >= 30 else "LOW")))
        ml_result = {
            "risk_percentage": round(risk_pct, 1),
            "risk_level": risk_lvl.upper(),
            "confidence_score": req.confidence_score if req.confidence_score is not None else None,
            "ml_source": "caller-override"
        }
    else:
        ml_result = trigger_ml_accident_model(bundle)

    pred_record = None
    if req.persist:
        pred_record = AccidentPrediction(
            start_road_id=road.road_id,
            end_road_id=road.road_id,
            start_location=road.road_name,
            end_location=road.road_name,
            prediction_time=now,
            risk_percentage=ml_result["risk_percentage"],
            risk_level=ml_result["risk_level"],
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred_record)

        if ml_result["risk_level"] in ["HIGH", "SEVERE", "CRITICAL"]:
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred_record.prediction_id,
                alert_type="ACCIDENT_RISK_WARNING",
                severity="CRITICAL" if ml_result["risk_level"] in ["CRITICAL", "SEVERE"] else "HIGH",
                message=f"Elevated accident risk ({ml_result['risk_percentage']}% - {ml_result['risk_level']}) predicted on {road.road_name}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)

        # Persist / update AccidentHotspot in DB
        if ml_result["risk_level"] in ["HIGH", "SEVERE", "CRITICAL"] or float(ml_result["risk_percentage"]) >= 50.0:
            h_lat, h_lng = None, None
            if road.start_location is not None:
                try:
                    pt = to_shape(road.start_location)
                    h_lat, h_lng = float(pt.y), float(pt.x)
                except Exception:
                    pass
            elif bundle.get("start_latitude") and bundle.get("start_longitude"):
                h_lat = float(bundle["start_latitude"])
                h_lng = float(bundle["start_longitude"])

            real_acc_count = db.query(Accident).filter(Accident.road_id == road.road_id).count()

            upsert_accident_hotspot(
                db=db,
                latitude=h_lat,
                longitude=h_lng,
                risk_level=ml_result["risk_level"],
                risk_score=float(ml_result["risk_percentage"]),
                accident_count=real_acc_count,
                zone_id=road.zone_id,
                calculated_at=now
            )

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
        created_new_road=created_new_road,
        created_at=now
    )


# =========================================================
# 3. INGESTION & PIPELINE APIS (FOR ML TEAM PIPELINES)
# =========================================================

@router.post(
    "/predictions/accidents",
    response_model=AccidentPredictionResponse,
    summary="Ingest Accident Risk Prediction (ML Pipeline)",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
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

    now = datetime.now()
    risk_level = pred_in.risk_level.upper()

    pred = AccidentPrediction(
        start_road_id=road.road_id,
        end_road_id=road.road_id,
        start_location=road.road_name,
        end_location=road.road_name,
        prediction_time=now,
        risk_percentage=pred_in.risk_percentage,
        risk_level=risk_level,
        confidence_score=pred_in.confidence_score,
        model_version_id=pred_in.model_version_id,
        created_at=now
    )
    db.add(pred)

    if risk_level in ["HIGH", "SEVERE", "CRITICAL"]:
        alert = Alert(
            road_id=road.road_id,
            prediction_id=pred.prediction_id,
            alert_type="ACCIDENT_RISK_WARNING",
            severity="CRITICAL" if risk_level in ["CRITICAL", "SEVERE"] else "HIGH",
            message=f"Elevated accident risk ({pred_in.risk_percentage:.1f}% - {risk_level}) predicted on {road.road_name}.",
            status="ACTIVE",
            created_at=now
        )
        db.add(alert)

        h_lat, h_lng = None, None
        if road.start_location is not None:
            try:
                pt = to_shape(road.start_location)
                h_lat, h_lng = float(pt.y), float(pt.x)
            except Exception:
                pass
        elif road.zone_id:
            zone = db.query(TrafficZone).filter(TrafficZone.zone_id == road.zone_id).first()
            if zone and zone.location is not None:
                try:
                    pt = to_shape(zone.location)
                    h_lat, h_lng = float(pt.y), float(pt.x)
                except Exception:
                    pass

        real_acc_count = db.query(Accident).filter(Accident.road_id == road.road_id).count()

        upsert_accident_hotspot(
            db=db,
            latitude=h_lat,
            longitude=h_lng,
            risk_level=risk_level,
            risk_score=float(pred_in.risk_percentage),
            accident_count=real_acc_count,
            zone_id=road.zone_id,
            calculated_at=now
        )

    db.commit()
    db.refresh(pred)

    return _format_accident_response(pred, road.road_name)


@router.post(
    "/ai/accidents/run-pipeline",
    response_model=AccidentPipelineRunResponse,
    summary="Run Accident Risk Pipeline across All Active Roads",
    dependencies=[Depends(require_roles("SUPER_ADMIN", "TRAFFIC_AUTHORITY"))]
)
def run_accident_pipeline(
    db: Session = Depends(get_db)
):
    roads = db.query(Road).filter(Road.is_active.is_(True)).all()
    now = datetime.now()

    predictions_count = 0
    alerts_count = 0

    for road in roads:
        bundle = resolve_route_bundle(db=db, road_id=road.road_id)
        ml_result = trigger_ml_accident_model(bundle)

        pred = AccidentPrediction(
            start_road_id=road.road_id,
            end_road_id=road.road_id,
            start_location=road.road_name,
            end_location=road.road_name,
            prediction_time=now,
            risk_percentage=ml_result["risk_percentage"],
            risk_level=ml_result["risk_level"],
            confidence_score=ml_result.get("confidence_score"),
            created_at=now
        )
        db.add(pred)
        predictions_count += 1

        if ml_result["risk_level"] in ["HIGH", "SEVERE", "CRITICAL"]:
            alert = Alert(
                road_id=road.road_id,
                prediction_id=pred.prediction_id,
                alert_type="ACCIDENT_RISK_WARNING",
                severity="CRITICAL" if ml_result["risk_level"] in ["CRITICAL", "SEVERE"] else "HIGH",
                message=f"Elevated accident risk ({ml_result['risk_percentage']}% - {ml_result['risk_level']}) predicted on {road.road_name}.",
                status="ACTIVE",
                created_at=now
            )
            db.add(alert)
            alerts_count += 1

            h_lat, h_lng = None, None
            if road.start_location is not None:
                try:
                    pt = to_shape(road.start_location)
                    h_lat, h_lng = float(pt.y), float(pt.x)
                except Exception:
                    pass
            elif bundle.get("start_latitude") and bundle.get("start_longitude"):
                h_lat = float(bundle["start_latitude"])
                h_lng = float(bundle["start_longitude"])

            real_acc_count = db.query(Accident).filter(Accident.road_id == road.road_id).count()

            upsert_accident_hotspot(
                db=db,
                latitude=h_lat,
                longitude=h_lng,
                risk_level=ml_result["risk_level"],
                risk_score=float(ml_result["risk_percentage"]),
                accident_count=real_acc_count,
                zone_id=road.zone_id,
                calculated_at=now
            )

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
    "/predictions/accidents/latest",
    response_model=List[AccidentPredictionResponse],
    summary="Get Latest Accident Risk Predictions Across Roads"
)
def get_latest_accident_predictions(
    db: Session = Depends(get_db)
):
    records = (
        db.query(AccidentPrediction)
        .order_by(AccidentPrediction.created_at.desc())
        .limit(20)
        .all()
    )

    return [_format_accident_response(p) for p in records]


@router.get(
    "/predictions/accidents/road/{road_id}",
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
        .filter(
            or_(
                AccidentPrediction.start_road_id == road_id,
                AccidentPrediction.end_road_id == road_id
            )
        )
        .order_by(AccidentPrediction.prediction_time.desc())
        .limit(limit)
        .all()
    )

    return [_format_accident_response(p, road.road_name) for p in records]
