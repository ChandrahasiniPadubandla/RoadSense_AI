import os
import math
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "final_traffic_anomaly_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "traffic_anomaly_scaler.pkl")
FEATURES_PATH = os.path.join(BASE_DIR, "traffic_anomaly_features.pkl")

# Load trained models & feature definitions
model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
features = joblib.load(FEATURES_PATH)


def _prepare_feature_row(traffic_data: dict) -> dict:
    """
    Transforms either raw or new API-aligned telemetry inputs
    into the exact 8 features expected by the trained Isolation Forest model.
    """
    # Case 1: Already formatted with new feature names
    if "speed_ratio" in traffic_data and "delay_ratio" in traffic_data:
        return {
            "speed_ratio": float(traffic_data.get("speed_ratio", 1.0)),
            "delay_ratio": float(traffic_data.get("delay_ratio", 0.0)),
            "slowdown_percentage": float(traffic_data.get("slowdown_percentage", 0.0)),
            "road_closure_flag": float(traffic_data.get("road_closure_flag", 0.0)),
            "rainfall_mm": float(traffic_data.get("rainfall_mm", 0.0)),
            "capacity_utilization": float(traffic_data.get("capacity_utilization", 0.5)),
            "hour_sin": float(traffic_data.get("hour_sin", 0.0)),
            "hour_cos": float(traffic_data.get("hour_cos", 1.0)),
        }

    # Case 2: Raw inputs (vehicle_count, average_speed, road_capacity, rainfall, hour...)
    avg_speed = float(traffic_data.get("average_speed", 35.0))
    speed_limit = float(traffic_data.get("speed_limit") or traffic_data.get("free_flow_speed") or 50.0)
    free_flow = max(10.0, speed_limit)
    
    speed_ratio = round(min(1.5, max(0.05, avg_speed / free_flow)), 3)
    
    # Slowdown percentage
    slowdown_pct = float(traffic_data.get("slowdown_percentage", 0.0))
    if slowdown_pct <= 0.0 and free_flow > 0:
        slowdown_pct = max(0.0, min(100.0, ((free_flow - avg_speed) / free_flow) * 100.0))
    
    # Delay ratio
    delay_sec = float(traffic_data.get("delay_seconds", 0.0))
    free_flow_sec = float(traffic_data.get("free_flow_seconds", 60.0))
    if free_flow_sec > 0 and delay_sec > 0:
        delay_ratio = round(min(5.0, delay_sec / free_flow_sec), 3)
    else:
        delay_ratio = round(min(5.0, (slowdown_pct / 100.0) * (free_flow / max(5.0, avg_speed))), 3)

    # Capacity utilization
    capacity = float(traffic_data.get("road_capacity", 2400.0))
    vehicles = float(traffic_data.get("vehicle_count", 600.0))
    capacity_utilization = round(min(2.0, max(0.05, vehicles / max(500.0, capacity))), 3)

    # Weather
    rainfall = float(traffic_data.get("rainfall", 0.0) or traffic_data.get("rainfall_mm", 0.0))

    # Road closure
    road_closure = 1.0 if (traffic_data.get("road_closure") or traffic_data.get("road_closure_flag")) else 0.0

    # Cyclical hour
    hour_val = float(traffic_data.get("hour", 12.0))
    hour_sin = round(math.sin(2.0 * math.pi * hour_val / 24.0), 4)
    hour_cos = round(math.cos(2.0 * math.pi * hour_val / 24.0), 4)

    return {
        "speed_ratio": speed_ratio,
        "delay_ratio": delay_ratio,
        "slowdown_percentage": slowdown_pct,
        "road_closure_flag": road_closure,
        "rainfall_mm": rainfall,
        "capacity_utilization": capacity_utilization,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
    }


def predict_anomaly(traffic_data: dict) -> dict:
    """
    Evaluates whether traffic conditions are NORMAL or an ANOMALY
    using the trained scale-invariant Isolation Forest model.
    """
    feature_row = _prepare_feature_row(traffic_data)

    df_in = pd.DataFrame([feature_row])[features]
    df_scaled = scaler.transform(df_in)

    raw_pred = model.predict(df_scaled)[0]
    decision_score = float(model.decision_function(df_scaled)[0])

    is_anomaly = bool(raw_pred == -1)
    status = "ANOMALY" if is_anomaly else "NORMAL"

    # Confidence score calculation based on margin from decision boundary
    # Decision score > 0 is normal, < 0 is anomaly
    confidence = round(min(99.0, max(60.0, 75.0 + abs(decision_score) * 200.0)), 1)

    return {
        "status": status,
        "prediction": status,
        "is_anomaly": is_anomaly,
        "anomaly_score": round(decision_score, 4),
        "confidence_score": confidence,
        "features_used": feature_row
    }
