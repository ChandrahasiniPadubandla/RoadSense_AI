import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from api_client import RoadSenseAPIClient


def run_model_inference_pipeline(client: RoadSenseAPIClient, artifacts_dir: str = "artifacts"):
    artifacts_path = Path(__file__).parent / artifacts_dir
    traffic_model_path = artifacts_path / "traffic_congestion_model.joblib"
    accident_model_path = artifacts_path / "accident_risk_model.joblib"

    if not traffic_model_path.exists() or not accident_model_path.exists():
        raise FileNotFoundError(
            f"Trained model artifacts not found in {artifacts_path}. Please run train_traffic_model.py and train_accident_model.py first."
        )

    print("=== Loading Trained ML Models ===")
    traffic_model = joblib.load(traffic_model_path)
    accident_model = joblib.load(accident_model_path)
    print("Models loaded successfully.")

    print("\n=== Fetching Current Live Data via REST APIs ===")
    roads = client.get_roads()
    traffic_records = client.get_traffic_records()
    weather_records = client.get_weather_records(limit=100)
    accidents = client.get_accidents()

    # Map latest traffic & weather by road_id
    latest_traffic_by_road = {}
    for tr in traffic_records:
        r_id = tr.get("road_id")
        if r_id not in latest_traffic_by_road:
            latest_traffic_by_road[r_id] = tr

    latest_weather_by_road = {}
    for wr in weather_records:
        r_id = wr.get("road_id")
        if r_id not in latest_weather_by_road:
            latest_weather_by_road[r_id] = wr

    road_crash_counts = pd.DataFrame(accidents)["road_id"].value_counts().to_dict() if accidents else {}

    now = datetime.utcnow()
    target_time = now + timedelta(minutes=30)
    hour = target_time.hour
    day_of_week = target_time.weekday()
    is_weekend = 1 if day_of_week in [5, 6] else 0

    print(f"\n=== Running Predictions for {len(roads)} Monitored Roads ===")
    traffic_preds_stored = 0
    accident_preds_stored = 0

    for road in roads:
        road_id = road.get("road_id")
        road_name = road.get("road_name", "Unknown")
        capacity = float(road.get("road_capacity") or 200.0)
        speed_limit = float(road.get("speed_limit") or 50.0)
        lanes = int(road.get("number_of_lanes") or 2)
        road_type = str(road.get("road_type") or "City Road")

        tr = latest_traffic_by_road.get(road_id, {})
        wr = latest_weather_by_road.get(road_id, {})

        vehicle_count = float(tr.get("vehicle_count") or (capacity * 0.6))
        avg_speed = float(tr.get("average_speed") or (speed_limit * 0.75))
        density = float(tr.get("traffic_density") or 60.0)
        rainfall = float(wr.get("rainfall") or tr.get("rainfall") or 0.0)
        temperature = float(wr.get("temperature") or tr.get("temperature") or 28.0)
        visibility = float(wr.get("visibility") or tr.get("visibility") or 1000.0)
        weather_cond = str(wr.get("weather_condition") or tr.get("weather_condition") or "Clear")
        road_cond = str(tr.get("road_condition") or "Normal")

        # -------------------------------------------------------------
        # 1. Traffic Congestion Inference
        # -------------------------------------------------------------
        cap_ratio = vehicle_count / max(capacity, 1.0)
        traffic_input = pd.DataFrame([{
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "vehicle_count": vehicle_count,
            "average_speed": avg_speed,
            "traffic_density": density,
            "road_capacity": capacity,
            "previous_traffic": vehicle_count,
            "capacity_ratio": cap_ratio,
            "rainfall": rainfall,
            "temperature": temperature,
            "visibility": visibility,
            "holiday": 0,
            "road_type": road_type,
            "weather_condition": weather_cond,
            "road_condition": road_cond
        }])

        predicted_congestion = str(traffic_model.predict(traffic_input)[0])
        conf_probs = traffic_model.predict_proba(traffic_input)[0]
        confidence = round(float(np.max(conf_probs)) * 100, 1)

        # Estimate future vehicle count based on prediction
        multiplier_map = {"LOW": 0.4, "MEDIUM": 0.7, "HIGH": 0.9, "SEVERE": 1.15}
        pred_veh_count = int(capacity * multiplier_map.get(predicted_congestion, 0.7))

        # Post prediction back to backend API
        traffic_payload = {
            "road_id": road_id,
            "target_time": target_time.isoformat(),
            "predicted_congestion": predicted_congestion,
            "predicted_vehicle_count": pred_veh_count,
            "confidence_score": confidence
        }
        res_t = client.post_traffic_prediction(traffic_payload)
        traffic_preds_stored += 1

        # -------------------------------------------------------------
        # 2. Accident Risk Inference
        # -------------------------------------------------------------
        hist_crashes = road_crash_counts.get(road_id, 0)
        accident_input = pd.DataFrame([{
            "traffic_density": density,
            "average_speed": avg_speed,
            "road_capacity": capacity,
            "historical_crashes": hist_crashes,
            "rainfall": rainfall,
            "visibility": visibility,
            "temperature": temperature,
            "vehicle_count": vehicle_count,
            "hour": hour,
            "holiday": 0,
            "weather_condition": weather_cond,
            "road_condition": road_cond,
            "road_type": road_type
        }])

        predicted_risk_level = str(accident_model.predict(accident_input)[0])
        risk_probs = accident_model.predict_proba(accident_input)[0]
        classes = list(accident_model.classes_)

        # Calculate calibrated risk percentage
        class_weights = {"LOW": 20.0, "MEDIUM": 50.0, "HIGH": 75.0, "CRITICAL": 92.0}
        risk_pct = round(sum(prob * class_weights.get(cls, 30.0) for cls, prob in zip(classes, risk_probs)), 1)
        acc_conf = round(float(np.max(risk_probs)) * 100, 1)

        accident_payload = {
            "road_id": road_id,
            "risk_percentage": risk_pct,
            "risk_level": predicted_risk_level,
            "confidence_score": acc_conf
        }
        res_a = client.post_accident_prediction(accident_payload)
        accident_preds_stored += 1

        print(f"[{road_name}] Congestion: {predicted_congestion} ({pred_veh_count} veh) | Accident Risk: {predicted_risk_level} ({risk_pct}%)")

    # 3. Trigger Anomaly Scan
    print("\n=== Running Anomaly Check via API ===")
    anomaly_res = client.trigger_anomaly_scan()
    print(f"Scanned roads: {anomaly_res.get('scanned_roads')}, Anomalies detected: {anomaly_res.get('anomalies_detected')}")

    print(f"\nSUCCESS: Stored {traffic_preds_stored} traffic predictions and {accident_preds_stored} accident predictions back to database via REST APIs!")


if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))
    from app.database.connection import SessionLocal
    from app.database.models import User
    from app.security import create_access_token

    db = SessionLocal()
    user = db.query(User).first()
    token = create_access_token(user.user_id)
    db.close()

    client = RoadSenseAPIClient(token=token)
    run_model_inference_pipeline(client)
