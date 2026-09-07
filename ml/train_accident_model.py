import os
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

from api_client import RoadSenseAPIClient


from typing import Optional
import argparse


def train_accident_model(
    client: Optional[RoadSenseAPIClient] = None,
    csv_path: Optional[str] = None,
    artifacts_dir: str = "artifacts"
):
    if csv_path:
        print(f"=== 1. Loading Accident Training Data from CSV: {csv_path} ===")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Training CSV file not found at: {csv_path}")
        full_df = pd.read_csv(csv_path)
        print(f"Loaded {len(full_df)} rows from CSV.")
    else:
        if not client:
            raise ValueError("Either a csv_path or an authenticated RoadSenseAPIClient must be provided.")
        print("=== 1. Fetching Data Exclusively via REST APIs ===")
        accidents = client.get_accidents()
        roads = client.get_roads()
        traffic = client.get_traffic_records()
        weather = client.get_weather_records()

        print(f"Fetched via API: {len(accidents)} accidents, {len(roads)} roads, {len(traffic)} traffic records, {len(weather)} weather records.")

        if not accidents:
            raise ValueError("No accidents returned from /api/accidents to train on.")

        df_accidents = pd.DataFrame(accidents)
        df_roads = pd.DataFrame(roads)
        df_traffic = pd.DataFrame(traffic)

        # 1. Calculate road historical accident frequency
        road_crash_counts = df_accidents["road_id"].value_counts().to_dict()

        # 2. Build Accident incidents dataset (High / Critical / Medium risk samples)
        accident_samples = []
        for _, acc in df_accidents.iterrows():
            road_id = acc.get("road_id")
            road_info = next((r for r in roads if r.get("road_id") == road_id), {})
            sev = str(acc.get("severity") or "MINOR").upper()

            if sev == "FATAL":
                risk_level = "CRITICAL"
                risk_pct = 95.0
            elif sev == "SEVERE":
                risk_level = "HIGH"
                risk_pct = 80.0
            elif sev == "MODERATE":
                risk_level = "MEDIUM"
                risk_pct = 50.0
            else:
                risk_level = "LOW"
                risk_pct = 25.0

            accident_samples.append({
                "road_id": road_id,
                "traffic_density": 75.0,  # Elevated density during crash
                "average_speed": float(road_info.get("speed_limit") or 50.0) * 1.15,
                "speed_limit": float(road_info.get("speed_limit") or 50.0),
                "number_of_lanes": int(road_info.get("number_of_lanes") or 2),
                "historical_crashes": road_crash_counts.get(road_id, 1),
                "rainfall": 15.0 if "rain" in str(acc.get("weather_condition", "")).lower() else 0.0,
                "weather_condition": str(acc.get("weather_condition") or "Clear"),
                "road_condition": str(acc.get("road_condition") or "Normal"),
                "road_type": str(road_info.get("road_type") or "City Road"),
                "risk_level": risk_level,
                "risk_pct": risk_pct
            })

        # 3. Build Normal Traffic samples (LOW / MEDIUM risk samples for balanced training)
        normal_samples = []
        for _, tr in df_traffic.head(len(accident_samples) * 2).iterrows():
            road_id = tr.get("road_id")
            road_info = next((r for r in roads if r.get("road_id") == road_id), {})

            density = float(tr.get("traffic_density") or 35.0)
            speed = float(tr.get("average_speed") or 45.0)
            limit = float(road_info.get("speed_limit") or 50.0)

            risk_level = "LOW"
            risk_pct = 15.0
            if density > 75:
                risk_level = "MEDIUM"
                risk_pct = 40.0

            normal_samples.append({
                "road_id": road_id,
                "traffic_density": density,
                "average_speed": speed,
                "speed_limit": limit,
                "number_of_lanes": int(road_info.get("number_of_lanes") or 2),
                "historical_crashes": road_crash_counts.get(road_id, 0),
                "rainfall": float(tr.get("rainfall") or 0.0),
                "weather_condition": str(tr.get("weather_condition") or "Clear"),
                "road_condition": str(tr.get("road_condition") or "Normal"),
                "road_type": str(road_info.get("road_type") or "City Road"),
                "risk_level": risk_level,
                "risk_pct": risk_pct
            })

        full_df = pd.DataFrame(accident_samples + normal_samples)

    # Column aliases for CSV variations
    aliases = {
        "density": "traffic_density",
        "speed": "average_speed",
        "avg_speed": "average_speed",
        "limit": "speed_limit",
        "capacity": "road_capacity",
        "volume": "vehicle_count",
        "lanes": "number_of_lanes",
        "crashes": "historical_crashes",
        "historical_accidents": "historical_crashes",
        "accident_count": "historical_crashes",
        "rain": "rainfall",
        "weather": "weather_condition",
        "surface": "road_condition",
        "type": "road_type",
        "severity": "risk_level",
        "accident_risk_level": "risk_level"
    }
    for alias, target in aliases.items():
        if alias in full_df.columns and target not in full_df.columns:
            full_df[target] = full_df[alias]

    if "road_capacity" not in full_df.columns:
        full_df["road_capacity"] = 500
    if "vehicle_count" not in full_df.columns:
        full_df["vehicle_count"] = 200
    if "holiday" not in full_df.columns:
        full_df["holiday"] = 0
    if "hour" not in full_df.columns:
        full_df["hour"] = 12

    num_cols = [
        "traffic_density", "average_speed", "road_capacity", "historical_crashes",
        "rainfall", "visibility", "temperature", "vehicle_count", "hour", "holiday"
    ]
    for col in num_cols:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors="coerce").fillna(0.0)
        else:
            full_df[col] = 0.0

    cat_cols = ["weather_condition", "road_condition", "road_type"]
    for col in cat_cols:
        if col in full_df.columns:
            full_df[col] = full_df[col].fillna("Unknown").astype(str)
        else:
            full_df[col] = "Unknown"

    # Derive or clean risk_level target
    if "risk_level" not in full_df.columns or full_df["risk_level"].isnull().all():
        # Derive risk level from density and speed ratio if not given
        ratios = full_df["average_speed"] / full_df["speed_limit"].replace(0, 50)
        conditions = [
            (full_df["traffic_density"] >= 80) & (ratios >= 1.2),
            (full_df["traffic_density"] >= 70) | (ratios >= 1.15),
            (full_df["traffic_density"] >= 50)
        ]
        choices = ["CRITICAL", "HIGH", "MEDIUM"]
        full_df["risk_level"] = np.select(conditions, choices, default="LOW")
    else:
        # Standardize labels
        mapper = {
            "FATAL": "CRITICAL",
            "SEVERE": "HIGH",
            "MODERATE": "MEDIUM",
            "MINOR": "LOW"
        }
        full_df["risk_level"] = full_df["risk_level"].astype(str).str.strip().str.upper()
        full_df["risk_level"] = full_df["risk_level"].replace(mapper)

    X = full_df[num_cols + cat_cols]
    y = full_df["risk_level"]

    print(f"Dataset shape: {X.shape}. Target classes distribution:")
    print(y.value_counts())

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
        ]
    )

    pipeline = Pipeline([
        ("prep", preprocessor),
        ("clf", RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42))
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("=== 2. Training High-Accuracy Random Forest Accident Risk Model ===")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy on Test Set: {acc * 100:.2f}%")
    print("\nClassification Report:\n", classification_report(y_test, y_pred, zero_division=0))

    # Save artifact
    out_dir = Path(__file__).parent / artifacts_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "accident_risk_model.joblib"
    joblib.dump(pipeline, model_path)
    print(f"Successfully exported trained model to: {model_path}")

    return pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Accident Risk ML Model")
    parser.add_argument("--csv", type=str, default=None, help="Optional path to training CSV file")
    args = parser.parse_args()
    data_dir = Path(__file__).parent / "data"
    csv_files = [f for f in data_dir.glob("*.csv") if f.is_file()]
    default_csv = csv_files[0] if csv_files else None

    if args.csv:
        train_accident_model(csv_path=args.csv)
    elif default_csv and default_csv.exists():
        print(f"Auto-detected dataset at {default_csv}. Training on dataset...")
        train_accident_model(csv_path=str(default_csv))
    else:
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
        train_accident_model(client=client)


