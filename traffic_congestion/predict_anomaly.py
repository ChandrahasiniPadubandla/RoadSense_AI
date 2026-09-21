import os
import joblib
import numpy as np
import pandas as pd
import warnings

# Suppress sklearn unpickle version warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Compatibility shim for scikit-learn unpickling across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------
# Resolve Model & Artifact Paths
# --------------------------------------------------
def _find_path(filename: str) -> str:
    # Check root directory first
    p1 = os.path.join(BASE_DIR, filename)
    if os.path.exists(p1):
        return p1
    # Check model/ subdirectory
    p2 = os.path.join(BASE_DIR, "model", filename)
    if os.path.exists(p2):
        return p2
    return p1

MODEL_PATH = _find_path("final_traffic_anomaly_model.pkl")
SCALER_PATH = _find_path("traffic_anomaly_scaler.pkl")
FEATURES_PATH = _find_path("traffic_anomaly_features.pkl")

# Load artifacts
anomaly_model = joblib.load(MODEL_PATH)
anomaly_scaler = joblib.load(SCALER_PATH)
anomaly_features = joblib.load(FEATURES_PATH)


def predict_anomaly(
    vehicle_count=None,
    average_speed=None,
    traffic_density=None,
    road_capacity=None,
    previous_traffic=None,
    hour=None,
    data=None
):
    """
    Predict whether traffic conditions are NORMAL or an ANOMALY using Isolation Forest.
    Accepts individual parameters, a dictionary, or a DataFrame.
    """
    details = predict_anomaly_detailed(
        vehicle_count=vehicle_count,
        average_speed=average_speed,
        traffic_density=traffic_density,
        road_capacity=road_capacity,
        previous_traffic=previous_traffic,
        hour=hour,
        data=data
    )
    return details["prediction"]


def predict_anomaly_detailed(
    vehicle_count=None,
    average_speed=None,
    traffic_density=None,
    road_capacity=None,
    previous_traffic=None,
    hour=None,
    data=None
):
    """
    Runs Isolation Forest anomaly detection and returns comprehensive metrics.
    """
    # If a dictionary or DataFrame was passed as first argument or data argument
    if isinstance(vehicle_count, (dict, pd.DataFrame)):
        data = vehicle_count
        vehicle_count = None

    if isinstance(data, dict):
        raw_dict = data
    elif isinstance(data, pd.DataFrame):
        raw_dict = data.iloc[0].to_dict()
    else:
        raw_dict = {
            "vehicle_count": vehicle_count if vehicle_count is not None else 800,
            "average_speed": average_speed if average_speed is not None else 35.0,
            "traffic_density": traffic_density if traffic_density is not None else 45.0,
            "road_capacity": road_capacity if road_capacity is not None else 1200,
            "previous_traffic": previous_traffic if previous_traffic is not None else 750,
            "hour": hour if hour is not None else 12
        }

    # Prepare DataFrame matching trained features
    input_data = {feat: [float(raw_dict.get(feat, 0.0))] for feat in anomaly_features}
    input_df = pd.DataFrame(input_data)[anomaly_features]

    # Transform through fitted scaler
    input_scaled = anomaly_scaler.transform(input_df)

    # Make prediction: 1 = Normal, -1 = Anomaly
    raw_pred = anomaly_model.predict(input_scaled)[0]
    is_anomaly = bool(raw_pred == -1)

    # Decision function (negative = anomaly, positive = inlier/normal)
    try:
        dec_func = float(anomaly_model.decision_function(input_scaled)[0])
        score_val = float(anomaly_model.score_samples(input_scaled)[0])
        # Higher distance from boundary means higher confidence
        confidence = round(min(max(abs(dec_func) * 300.0, 55.0), 99.0), 1)
    except Exception:
        dec_func = 0.0
        score_val = 0.0
        confidence = 85.0

    return {
        "prediction": "ANOMALY" if is_anomaly else "NORMAL",
        "is_anomaly": is_anomaly,
        "raw_prediction": int(raw_pred),
        "anomaly_score": round(float(dec_func), 4),
        "sample_score": round(float(score_val), 4),
        "confidence_score": float(confidence),
        "features_used": {feat: float(raw_dict.get(feat, 0.0)) for feat in anomaly_features}
    }


if __name__ == "__main__":
    # Test normal traffic scenario
    normal_sample = {
        "vehicle_count": 850,
        "average_speed": 35.5,
        "traffic_density": 50.0,
        "road_capacity": 1500,
        "previous_traffic": 820,
        "hour": 14
    }
    print("Normal Sample Test:")
    print(predict_anomaly_detailed(normal_sample))

    # Test extreme anomaly scenario (huge vehicle surge, stalled speed)
    anomaly_sample = {
        "vehicle_count": 4800,
        "average_speed": 2.1,
        "traffic_density": 98.5,
        "road_capacity": 1000,
        "previous_traffic": 600,
        "hour": 3
    }
    print("\nAnomaly Sample Test:")
    print(predict_anomaly_detailed(anomaly_sample))
