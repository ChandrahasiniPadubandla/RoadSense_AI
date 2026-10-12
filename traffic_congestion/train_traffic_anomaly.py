import os
import math
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "hyderabad_traffic_accident_15000.csv")

# Standard speed limits by Indian IRC road classification
ROAD_TYPE_FREE_FLOW = {
    "Expressway": 80.0,
    "Highway": 65.0,
    "Arterial Road": 50.0,
    "Urban Road": 40.0,
    "Residential Road": 30.0,
}

FEATURE_COLUMNS = [
    "speed_ratio",
    "delay_ratio",
    "slowdown_percentage",
    "road_closure_flag",
    "rainfall_mm",
    "capacity_utilization",
    "hour_sin",
    "hour_cos"
]


def load_and_transform_dataset():
    print(f"Loading raw dataset from: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"Loaded {len(df)} records.")

    # 1. Map free-flow speeds based on IRC road classification
    df["free_flow_speed"] = df["road_type"].map(ROAD_TYPE_FREE_FLOW).fillna(50.0)

    # 2. Derive scale-invariant features
    df["speed_ratio"] = (df["average_speed"] / df["free_flow_speed"]).clip(0.05, 1.5)
    
    # Slowdown percentage relative to free-flow
    df["slowdown_percentage"] = (
        np.maximum(0.0, (df["free_flow_speed"] - df["average_speed"]) / df["free_flow_speed"]) * 100.0
    ).clip(0.0, 100.0)

    # Delay ratio: estimated delay / free-flow transit time
    df["delay_ratio"] = (
        (df["slowdown_percentage"] / 100.0) * (df["free_flow_speed"] / df["average_speed"].clip(lower=5.0))
    ).clip(0.0, 5.0)

    # Capacity utilization: vehicle count relative to road capacity
    df["capacity_utilization"] = (df["vehicle_count"] / df["road_capacity"]).clip(0.05, 2.0)

    # Rainfall in mm
    df["rainfall_mm"] = df["rainfall"].fillna(0.0).clip(lower=0.0)

    # Road closure flag: 0 for normal baseline, inject small synthetic closure sample
    df["road_closure_flag"] = 0.0

    # Cyclical hour encoding
    hour_val = df["hour"].fillna(12.0)
    df["hour_sin"] = np.sin(2.0 * np.pi * hour_val / 24.0)
    df["hour_cos"] = np.cos(2.0 * np.pi * hour_val / 24.0)

    # Add realistic edge anomalies (severe roadblocks / gridlock / closures)
    num_anomalies = 450
    closure_records = []
    for _ in range(num_anomalies):
        h = np.random.uniform(0, 24)
        is_closed = 1.0 if np.random.rand() > 0.3 else 0.0
        closure_records.append({
            "speed_ratio": np.random.uniform(0.05, 0.40),
            "delay_ratio": np.random.uniform(1.5, 5.0),
            "slowdown_percentage": np.random.uniform(50.0, 95.0),
            "road_closure_flag": is_closed,
            "rainfall_mm": np.random.uniform(0.0, 5.0),  # Not weather-related -> true incident
            "capacity_utilization": np.random.uniform(0.8, 1.8),
            "hour_sin": math.sin(2.0 * math.pi * h / 24.0),
            "hour_cos": math.cos(2.0 * math.pi * h / 24.0),
        })

    anomaly_df = pd.DataFrame(closure_records)
    X = pd.concat([df[FEATURE_COLUMNS], anomaly_df], ignore_index=True)
    return X


def train():
    X = load_and_transform_dataset()
    print("\nFeature Summary Statistics:")
    print(X.describe().T[["mean", "std", "min", "50%", "max"]])

    # Train / test split for validation
    X_train, X_test = train_test_split(X, test_size=0.20, random_state=42)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train Isolation Forest with 3% calibrated contamination
    print("\nTraining Isolation Forest model...")
    model = IsolationForest(
        n_estimators=120,
        contamination=0.03,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled)

    # Test predictions
    preds = model.predict(X_test_scaled)
    normal_cnt = np.sum(preds == 1)
    anomaly_cnt = np.sum(preds == -1)
    print(f"Validation Test Results: Normal = {normal_cnt} ({normal_cnt/len(preds)*100:.1f}%), Anomalies = {anomaly_cnt} ({anomaly_cnt/len(preds)*100:.1f}%)")

    # Fit final model on complete dataset
    print("\nFitting final model on all 15,150 transformed observations...")
    final_scaler = StandardScaler()
    X_full_scaled = final_scaler.fit_transform(X)

    final_model = IsolationForest(
        n_estimators=120,
        contamination=0.03,
        random_state=42,
        n_jobs=-1
    )
    final_model.fit(X_full_scaled)

    # Save artifacts
    model_path = os.path.join(BASE_DIR, "final_traffic_anomaly_model.pkl")
    scaler_path = os.path.join(BASE_DIR, "traffic_anomaly_scaler.pkl")
    features_path = os.path.join(BASE_DIR, "traffic_anomaly_features.pkl")

    joblib.dump(final_model, model_path)
    joblib.dump(final_scaler, scaler_path)
    joblib.dump(FEATURE_COLUMNS, features_path)

    print(f"\nSaved trained model: {model_path}")
    print(f"Saved scaler: {scaler_path}")
    print(f"Saved feature list: {features_path}")
    print("Features:", FEATURE_COLUMNS)

    # Validation on test cases
    print("\nRunning Verification Test Cases:")
    test_cases = [
        {
            "name": "Normal Flow on Uppal Main Road (35 km/h on 50 km/h, clear weather, 3100 cap)",
            "data": {
                "speed_ratio": 35.0 / 50.0,
                "delay_ratio": 0.05,
                "slowdown_percentage": 10.0,
                "road_closure_flag": 0.0,
                "rainfall_mm": 0.0,
                "capacity_utilization": 500 / 3100,
                "hour_sin": math.sin(2 * math.pi * 14 / 24),
                "hour_cos": math.cos(2 * math.pi * 14 / 24),
            }
        },
        {
            "name": "Normal Heavy Rain Flow (18 km/h with 45mm rain)",
            "data": {
                "speed_ratio": 18.0 / 50.0,
                "delay_ratio": 0.35,
                "slowdown_percentage": 50.0,
                "road_closure_flag": 0.0,
                "rainfall_mm": 45.0,
                "capacity_utilization": 1200 / 3100,
                "hour_sin": math.sin(2 * math.pi * 18 / 24),
                "hour_cos": math.cos(2 * math.pi * 18 / 24),
            }
        },
        {
            "name": "Severe Anomaly (5 km/h on 60 km/h road, dry weather, closure/breakdown)",
            "data": {
                "speed_ratio": 5.0 / 60.0,
                "delay_ratio": 3.8,
                "slowdown_percentage": 91.0,
                "road_closure_flag": 1.0,
                "rainfall_mm": 0.0,
                "capacity_utilization": 1.45,
                "hour_sin": math.sin(2 * math.pi * 11 / 24),
                "hour_cos": math.cos(2 * math.pi * 11 / 24),
            }
        }
    ]

    for tc in test_cases:
        df_tc = pd.DataFrame([tc["data"]])[FEATURE_COLUMNS]
        tc_scaled = final_scaler.transform(df_tc)
        pred = final_model.predict(tc_scaled)[0]
        score = final_model.decision_function(tc_scaled)[0]
        status = "ANOMALY" if pred == -1 else "NORMAL"
        print(f" -> {tc['name']}: {status} (decision score = {score:.4f})")


if __name__ == "__main__":
    train()
