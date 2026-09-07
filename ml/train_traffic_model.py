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


def train_traffic_model(
    client: Optional[RoadSenseAPIClient] = None,
    csv_path: Optional[str] = None,
    artifacts_dir: str = "artifacts"
):
    if csv_path:
        print(f"=== 1. Loading Traffic Training Data from CSV: {csv_path} ===")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Training CSV file not found at: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} rows from CSV.")
    else:
        if not client:
            raise ValueError("Either a csv_path or an authenticated RoadSenseAPIClient must be provided.")
        print("=== 1. Fetching Data Exclusively via REST APIs ===")
        roads = client.get_roads()
        zones = client.get_zones()
        traffic_records = client.get_traffic_records()
        weather_records = client.get_weather_records()

        print(f"Fetched via API: {len(roads)} roads, {len(zones)} zones, {len(traffic_records)} traffic records, {len(weather_records)} weather records.")

        if not traffic_records:
            raise ValueError("No traffic records returned from /api/traffic to train on.")

        # Convert to DataFrames
        df_traffic = pd.DataFrame(traffic_records)
        df_roads = pd.DataFrame(roads)
        df_weather = pd.DataFrame(weather_records)

        # Merge traffic records with road characteristics
        df = df_traffic.merge(
            df_roads[["road_id", "road_type", "road_capacity", "speed_limit", "number_of_lanes"]],
            on="road_id",
            how="left"
        )

    # Temporal feature engineering
    if "timestamp" in df.columns or "datetime" in df.columns:
        ts_col = "timestamp" if "timestamp" in df.columns else "datetime"
        df["dt"] = pd.to_datetime(df[ts_col], errors="coerce")
        df["hour"] = df["dt"].dt.hour.fillna(12).astype(int)
        df["day_of_week"] = df["dt"].dt.dayofweek.fillna(0).astype(int)
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    else:
        if "hour" not in df.columns:
            df["hour"] = 12
        if "day_of_week" not in df.columns:
            df["day_of_week"] = 0
        elif df["day_of_week"].dtype == object:
            day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
            df["day_of_week"] = df["day_of_week"].map(day_map).fillna(0).astype(int)
        if "is_weekend" not in df.columns:
            df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # Column aliases support for diverse CSV formats
    aliases = {
        "volume": "vehicle_count",
        "vehicles": "vehicle_count",
        "speed": "average_speed",
        "avg_speed": "average_speed",
        "density": "traffic_density",
        "capacity": "road_capacity",
        "lanes": "number_of_lanes",
        "rain": "rainfall",
        "temp": "temperature",
        "vis": "visibility",
        "weather": "weather_condition",
        "surface": "road_condition",
        "type": "road_type"
    }
    for alias, target in aliases.items():
        if alias in df.columns and target not in df.columns:
            df[target] = df[alias]

    # Additional high-impact feature engineering
    if "road_capacity" in df.columns and "vehicle_count" in df.columns:
        df["capacity_ratio"] = (pd.to_numeric(df["vehicle_count"], errors="coerce").fillna(0) / 
                                pd.to_numeric(df["road_capacity"], errors="coerce").replace(0, 1).fillna(1))
    else:
        df["capacity_ratio"] = 0.5

    if "previous_traffic" not in df.columns:
        df["previous_traffic"] = df.get("vehicle_count", 0)

    if "holiday" not in df.columns:
        df["holiday"] = 0

    # Clean numerical columns
    num_cols = [
        "vehicle_count", "average_speed", "traffic_density", "road_capacity",
        "previous_traffic", "capacity_ratio", "rainfall", "temperature", "visibility",
        "hour", "day_of_week", "is_weekend", "holiday"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    # Categorical columns
    cat_cols = ["road_type", "weather_condition", "road_condition"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)
        else:
            df[col] = "Unknown"

    # Derive or clean target variable: congestion_level
    if "congestion_level" not in df.columns or df["congestion_level"].isnull().all():
        cap = df["road_capacity"].replace(0, 200)
        ratio = df["vehicle_count"] / cap
        conditions = [
            ratio >= 0.85,
            ratio >= 0.65,
            ratio >= 0.40
        ]
        choices = ["SEVERE", "HIGH", "MEDIUM"]
        df["congestion_level"] = np.select(conditions, choices, default="LOW")
    else:
        df["congestion_level"] = df["congestion_level"].str.strip().str.upper().fillna("LOW")

    features = num_cols + cat_cols
    X = df[features]
    y = df["congestion_level"]

    print(f"Dataset shape: {X.shape}. Target classes distribution:")
    print(y.value_counts())

    # Build Preprocessing & Pipeline
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

    print("=== 2. Training High-Accuracy Random Forest Congestion Model ===")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy on Test Set: {acc * 100:.2f}%")
    print("\nClassification Report:\n", classification_report(y_test, y_pred, zero_division=0))

    # Save artifact
    out_dir = Path(__file__).parent / artifacts_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "traffic_congestion_model.joblib"
    joblib.dump(pipeline, model_path)
    print(f"Successfully exported trained model to: {model_path}")

    return pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Traffic Congestion ML Model")
    parser.add_argument("--csv", type=str, default=None, help="Optional path to training CSV file")
    args = parser.parse_args()
    data_dir = Path(__file__).parent / "data"
    csv_files = [f for f in data_dir.glob("*.csv") if f.is_file()]
    default_csv = csv_files[0] if csv_files else None

    if args.csv:
        train_traffic_model(csv_path=args.csv)
    elif default_csv and default_csv.exists():
        print(f"Auto-detected dataset at {default_csv}. Training on dataset...")
        train_traffic_model(csv_path=str(default_csv))
    else:
        import sys
        sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))
        from app.database.connection import SessionLocal
        from app.database.models import User
        from app.security import create_access_token
        from app.database.models import User
        from app.security import create_access_token

        db = SessionLocal()
        user = db.query(User).first()
        token = create_access_token(user.user_id)
        db.close()

        client = RoadSenseAPIClient(token=token)
        train_traffic_model(client=client)


