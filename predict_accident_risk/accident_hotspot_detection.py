import os
import sys
import math
import argparse
from typing import Optional, Dict, Any, Tuple
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Ensure standard output can handle utf-8 characters without cp1252 crashes
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PIPELINE_PATH = os.path.join(BASE_DIR, "hotspot_model_pipeline.pkl")
HISTORICAL_CSV_PATH = os.path.join(BASE_DIR, "accident_hotspots.csv")

# Known landmark coordinates across the Hyderabad metropolitan region
HYDERABAD_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "Financial District": (17.4141, 78.3444),
    "Nanakramguda": (17.4212, 78.3428),
    "Tolichowki": (17.4037, 78.4150),
    "Gachibowli": (17.4401, 78.3489),
    "Madhapur": (17.4401, 78.3910),
    "Jubilee Hills": (17.4326, 78.4071),
    "LB Nagar": (17.3457, 78.5522),
    "Dilsukhnagar": (17.3688, 78.5247),
    "Hitech City": (17.4483, 78.3915),
    "HITEC City": (17.4483, 78.3808),
    "Ameerpet": (17.4375, 78.4483),
    "Punjagutta": (17.4260, 78.4525),
    "Kondapur": (17.4700, 78.3660),
    "Kompally": (17.5450, 78.4870),
    "Secunderabad": (17.4399, 78.4983),
    "Mehdipatnam": (17.3945, 78.4420),
    "Tarnaka": (17.4280, 78.5430),
    "Uppal": (17.4050, 78.5590),
    "Malakpet": (17.3731, 78.5010),
    "Charminar": (17.3616, 78.4747),
    "Begumpet": (17.4447, 78.4660),
    "Miyapur": (17.4969, 78.3568),
    "Kukatpally": (17.4849, 78.4138),
    "Bachupally": (17.5480, 78.3670),
    "Koti": (17.3846, 78.4865),
    "ECIL": (17.4760, 78.5710),
    "Raidurg": (17.4239, 78.3782),
    "Attapur": (17.3680, 78.4250),
    "Rajendranagar": (17.3196, 78.4310),
    "Lakdikapul": (17.4000, 78.4597),
    "Shamshabad": (17.2510, 78.4380),
    "Banjara Hills": (17.4126, 78.4482),
    "Somajiguda": (17.4241, 78.4583),
    "Khairatabad": (17.4123, 78.4608),
    "Nampally": (17.3890, 78.4625),
    "Abids": (17.3917, 78.4764),
    "Alwal": (17.5020, 78.5070),
    "Bowenpally": (17.4700, 78.4620),
    "Chandrayangutta": (17.3300, 78.4715),
    "Manikonda": (17.4050, 78.3790),
    "Narsingi": (17.3850, 78.3250),
    "IDPL": (17.4950, 78.4350),
    "Moosapet": (17.4660, 78.4230),
    "Balanagar": (17.4700, 78.4380),
    "Chintal": (17.5020, 78.4380),
    "Erragadda": (17.4520, 78.4320),
    "Sanathnagar": (17.4580, 78.4410),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates approximate distance between two GPS coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def resolve_coordinates(location_name: str) -> Optional[Tuple[float, float]]:
    """Resolves coordinates for a known Hyderabad location name."""
    if not location_name:
        return None
    clean = location_name.strip().lower()

    # Exact match
    for name, coords in HYDERABAD_LOCATIONS.items():
        if name.lower() == clean:
            return coords

    # Partial / substring match
    for name, coords in HYDERABAD_LOCATIONS.items():
        if name.lower() in clean or clean in name.lower():
            return coords

    return None


def get_risk_level(risk: float) -> str:
    """Convert average risk into categorical risk level."""
    risk_val = float(risk or 0.0)
    if risk_val < 30.0:
        return "LOW"
    elif risk_val < 55.0:
        return "MEDIUM"
    elif risk_val < 75.0:
        return "HIGH"
    else:
        return "SEVERE"


def get_dataset_path() -> str:
    """Finds the dataset file across potential local locations."""
    candidates = [
        os.path.join(BASE_DIR, "dataset", "hyderabad_traffic_accident_15000.csv"),
        os.path.join(BASE_DIR, "dataset", "hyderabad_traffic_accident_balanced_15000.csv"),
        os.path.join("dataset", "hyderabad_traffic_accident_15000.csv"),
        os.path.join("dataset", "hyderabad_traffic_accident_balanced_15000.csv"),
        os.path.join("predict_accident_risk", "dataset", "hyderabad_traffic_accident_15000.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "Could not locate dataset 'hyderabad_traffic_accident_15000.csv' in expected directories."
    )


def load_accidents_dataset(dataset_path: Optional[str] = None) -> pd.DataFrame:
    """Loads and filters only records where an accident occurred."""
    path = dataset_path or get_dataset_path()
    df = pd.read_csv(path)
    return df[df["accident_occurred"] == 1].copy()


def train_hotspot_model(
    dataset_path: Optional[str] = None,
    output_model_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trains a Machine Learning Pipeline from the dataset CSV.
    The model learns to predict whether ANY route (known or new) is an accident hotspot,
    its hotspot probability, and its expected accident risk score.
    """
    csv_file = dataset_path or get_dataset_path()
    print(f"Training Hotspot ML Model using dataset: {csv_file}...")
    df = pd.read_csv(csv_file)

    # Compute corridor distance
    def calc_dist(row):
        return haversine_distance(
            row["start_latitude"], row["start_longitude"],
            row["end_latitude"], row["end_longitude"]
        )

    df["distance_km"] = df.apply(calc_dist, axis=1)

    # Ground truth: Hotspot corridor indicates elevated accident risk (>= 55.0% - HIGH/SEVERE)
    # or an actual recorded accident
    df["is_hotspot"] = ((df["accident_risk"] >= 55.0) | (df["accident_occurred"] == 1)).astype(int)

    feature_cols = [
        "start_latitude", "start_longitude", "end_latitude", "end_longitude", "distance_km",
        "road_type", "hour", "day_of_week", "vehicle_count", "average_speed",
        "traffic_density", "road_capacity", "weather", "rainfall", "road_condition",
        "congestion_level"
    ]

    num_cols = [
        "start_latitude", "start_longitude", "end_latitude", "end_longitude", "distance_km",
        "hour", "vehicle_count", "average_speed", "traffic_density", "road_capacity", "rainfall"
    ]
    cat_cols = ["road_type", "day_of_week", "weather", "road_condition", "congestion_level"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ]
    )

    # 1. Classifier: Predicts whether the route is an Accident Hotspot & Hotspot Probability
    cls_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=80, max_depth=12, random_state=42, n_jobs=-1))
    ])
    cls_pipeline.fit(df[feature_cols], df["is_hotspot"])

    # 2. Regressor: Predicts expected Accident Risk Percentage (0.0 to 100.0%)
    reg_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", GradientBoostingRegressor(n_estimators=80, max_depth=5, random_state=42))
    ])
    reg_pipeline.fit(df[feature_cols], df["accident_risk"])

    artifact = {
        "classifier": cls_pipeline,
        "regressor": reg_pipeline,
        "features": feature_cols,
        "num_cols": num_cols,
        "cat_cols": cat_cols,
    }

    dest = output_model_path or MODEL_PIPELINE_PATH
    joblib.dump(artifact, dest)
    print(f"Hotspot ML Model successfully trained and saved to: {dest}")
    return artifact


def load_or_train_model(model_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads existing trained hotspot model, or automatically trains from CSV if missing."""
    target_path = model_path or MODEL_PIPELINE_PATH
    if os.path.exists(target_path):
        try:
            return joblib.load(target_path)
        except Exception as exc:
            print(f"Error loading {target_path} ({exc}). Re-training model...")

    return train_hotspot_model(output_model_path=target_path)


def detect_all_hotspots(
    dataset_path: Optional[str] = None,
    save_csv: bool = False,
    output_csv_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Groups accidents across Hyderabad by route corridor from the CSV records:
    (start_location, end_location, start_latitude, start_longitude, end_latitude, end_longitude).
    Calculates total accidents, average risk score, and risk classification.
    """
    accidents = load_accidents_dataset(dataset_path)

    hotspots = (
        accidents.groupby([
            "start_location",
            "end_location",
            "start_latitude",
            "start_longitude",
            "end_latitude",
            "end_longitude",
        ])
        .agg(
            accidents=("accident_occurred", "sum"),
            average_risk=("accident_risk", "mean"),
        )
        .reset_index()
    )

    hotspots["risk"] = hotspots["average_risk"].apply(get_risk_level)

    hotspots = hotspots.sort_values(
        by="accidents",
        ascending=False
    ).reset_index(drop=True)

    hotspots.insert(0, "hotspot_id", range(1, len(hotspots) + 1))

    if save_csv:
        csv_dest = output_csv_path or HISTORICAL_CSV_PATH
        hotspots.to_csv(csv_dest, index=False)
        print(f"\nHistorical hotspot results saved to {csv_dest}")

    return hotspots


def predict_new_route_hotspot(
    start_location: str,
    end_location: str,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    end_latitude: Optional[float] = None,
    end_longitude: Optional[float] = None,
    road_type: str = "Arterial Road",
    hour: Optional[int] = None,
    day_of_week: Optional[str] = None,
    vehicle_count: Optional[int] = None,
    average_speed: Optional[float] = None,
    traffic_density: Optional[float] = None,
    road_capacity: int = 1400,
    weather: Optional[str] = None,
    rainfall: Optional[float] = None,
    road_condition: Optional[str] = None,
    congestion_level: Optional[str] = None,
    model_artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from datetime import datetime
    now = datetime.now()
    cur_hour = hour if hour is not None else now.hour
    cur_day = day_of_week if day_of_week is not None else now.strftime("%A")
    cur_weather = weather or "Clear"
    cur_rainfall = rainfall if rainfall is not None else (12.0 if cur_weather in ["Rain", "Thunderstorm"] else 0.0)
    cur_cond = road_condition or ("Wet" if cur_rainfall > 1.0 else "Good")
    """
    Uses the Machine Learning Model (trained on the dataset CSV) to predict whether
    a BRAND NEW route is an accident hotspot, and calculates its predicted risk percentage
    and risk category.
    """
    model = model_artifact or load_or_train_model()
    cls_pipeline = model["classifier"]
    reg_pipeline = model["regressor"]

    # 1. Resolve coordinates if not explicitly passed
    s_coords = (start_latitude, start_longitude) if (start_latitude is not None and start_longitude is not None) else resolve_coordinates(start_location)
    e_coords = (end_latitude, end_longitude) if (end_latitude is not None and end_longitude is not None) else resolve_coordinates(end_location)

    s_lat, s_lng = s_coords if s_coords else (17.4400, 78.4400)
    e_lat, e_lng = e_coords if e_coords else (17.4500, 78.4500)

    # 2. Compute corridor distance
    dist = haversine_distance(s_lat, s_lng, e_lat, e_lng)
    if dist < 0.2:
        dist = 2.5  # reasonable urban corridor baseline

    # 3. Dynamic baseline traffic features if not explicitly provided
    dens = traffic_density if traffic_density is not None else (75.0 if cur_hour in [8, 9, 10, 17, 18, 19, 20] else 45.0)
    spd = average_speed if average_speed is not None else (25.0 if dens > 70.0 else 42.0)
    veh = vehicle_count if vehicle_count is not None else int(road_capacity * (dens / 100.0))
    cong = congestion_level if congestion_level is not None else ("HIGH" if dens > 70.0 else ("MEDIUM" if dens > 45.0 else "LOW"))

    feature_dict = {
        "start_latitude": float(s_lat),
        "start_longitude": float(s_lng),
        "end_latitude": float(e_lat),
        "end_longitude": float(e_lng),
        "distance_km": float(dist),
        "road_type": road_type,
        "hour": int(cur_hour),
        "day_of_week": cur_day,
        "vehicle_count": int(veh),
        "average_speed": float(spd),
        "traffic_density": float(dens),
        "road_capacity": int(road_capacity),
        "weather": cur_weather,
        "rainfall": float(cur_rainfall),
        "road_condition": cur_cond,
        "congestion_level": cong,
    }

    df_in = pd.DataFrame([feature_dict])

    # 4. ML Model Inference
    pred_hotspot = bool(cls_pipeline.predict(df_in)[0])
    hotspot_prob = float(cls_pipeline.predict_proba(df_in)[0][1] * 100.0)
    pred_risk = float(np.clip(reg_pipeline.predict(df_in)[0], 0.0, 100.0))
    risk_level = get_risk_level(pred_risk)

    # A route is classified as an accident hotspot if ML hotspot probability >= 50%
    # or predicted risk is in HIGH/SEVERE tier (>= 55.0%)
    is_hotspot = pred_hotspot or hotspot_prob >= 50.0 or pred_risk >= 55.0

    contributing_factors = []
    if dens > 70.0:
        contributing_factors.append(f"Elevated traffic density ({dens:.1f}%) on corridor")
    if spd < 25.0:
        contributing_factors.append(f"Severe speed slowdown ({spd:.1f} km/h)")
    if cur_rainfall > 1.0:
        contributing_factors.append(f"Adverse weather / rain conditions ({cur_rainfall} mm)")
    if dist > 8.0:
        contributing_factors.append(f"Extended multi-junction arterial corridor ({dist:.1f} km)")
    if not contributing_factors:
        contributing_factors.append("Moderate urban traffic corridor")

    return {
        "found": True,
        "is_hotspot": is_hotspot,
        "hotspot_id": None,
        "source": "ml_model_prediction",
        "is_new_route": True,
        "start_location": start_location,
        "end_location": end_location,
        "start_latitude": round(s_lat, 6),
        "start_longitude": round(s_lng, 6),
        "end_latitude": round(e_lat, 6),
        "end_longitude": round(e_lng, 6),
        "distance_km": dist,
        "accidents": None,
        "average_risk": round(pred_risk, 2),
        "predicted_risk": round(pred_risk, 2),
        "hotspot_probability": round(hotspot_prob, 1),
        "risk": risk_level,
        "contributing_factors": contributing_factors,
        "message": (
            f"ML Model Prediction for NEW ROUTE: {start_location} -> {end_location} "
            f"| Hotspot: {'YES' if is_hotspot else 'NO'} (Probability: {hotspot_prob:.1f}%) "
            f"| Predicted Risk: {pred_risk:.2f}% ({risk_level})."
        ),
    }


def detect_hotspot(
    start_location: str,
    end_location: str,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    end_latitude: Optional[float] = None,
    end_longitude: Optional[float] = None,
    hotspots_df: Optional[pd.DataFrame] = None,
    hour: Optional[int] = None,
    day_of_week: Optional[str] = None,
    weather: Optional[str] = None,
    rainfall: Optional[float] = None,
    traffic_density: Optional[float] = None,
    force_ml: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates whether the route between start_location and end_location is an accident hotspot:
    1. First checks if historical empirical records exist in the CSV.
    2. If NOT in the CSV (NEW ROUTE), runs the trained ML Model to predict the route's hotspot
       status, hotspot probability, and accident risk score.
    """
    if hotspots_df is None:
        if os.path.exists(HISTORICAL_CSV_PATH):
            hotspots_df = pd.read_csv(HISTORICAL_CSV_PATH)
        else:
            hotspots_df = detect_all_hotspots(save_csv=False)

    clean_start = str(start_location).strip().lower()
    clean_end = str(end_location).strip().lower()

    # 1. Direct and reverse historical matching
    direct_match = hotspots_df[
        hotspots_df["start_location"].str.lower().str.contains(clean_start, na=False, regex=False)
        & hotspots_df["end_location"].str.lower().str.contains(clean_end, na=False, regex=False)
    ]

    reverse_match = pd.DataFrame()
    if direct_match.empty:
        reverse_match = hotspots_df[
            hotspots_df["start_location"].str.lower().str.contains(clean_end, na=False, regex=False)
            & hotspots_df["end_location"].str.lower().str.contains(clean_start, na=False, regex=False)
        ]

    matched_row = None
    is_reverse = False
    if not direct_match.empty:
        matched_row = direct_match.iloc[0]
    elif not reverse_match.empty:
        matched_row = reverse_match.iloc[0]
        is_reverse = True

    # 2. Always run ML Model prediction for live, dynamic corridor assessment
    pred = predict_new_route_hotspot(
        start_location=start_location,
        end_location=end_location,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        end_latitude=end_latitude,
        end_longitude=end_longitude,
        hour=hour,
        day_of_week=day_of_week,
        weather=weather,
        rainfall=rainfall,
        traffic_density=traffic_density,
    )

    # 3. Enrich with historical empirical database/CSV statistics if available
    if matched_row is not None:
        acc_count = int(matched_row["accidents"])
        avg_risk = float(matched_row["average_risk"])
        pred["has_historical_data"] = True
        pred["historical_accidents"] = acc_count
        pred["historical_risk"] = round(avg_risk, 2)
        pred["is_new_route"] = False
        pred["hotspot_id"] = int(matched_row["hotspot_id"])
        if acc_count >= 15 or avg_risk >= 55.0:
            pred["is_hotspot"] = True
        pred["message"] = (
            f"AI / ML Model Prediction: Route corridor {start_location} -> {end_location} ({pred['distance_km']} km) "
            f"has {pred['predicted_risk']:.1f}% predicted risk ({pred['risk']}, {pred['hotspot_probability']:.1f}% probability). "
            f"Corridor has {acc_count} recorded historical accidents ({avg_risk:.1f}% avg risk)."
        )
    else:
        pred["has_historical_data"] = False
        pred["historical_accidents"] = 0
        pred["historical_risk"] = None
        pred["is_new_route"] = True

    return pred


def main():
    parser = argparse.ArgumentParser(
        description="Hyderabad Accident Hotspot Detection & ML Prediction Pipeline (RoadSense AI)"
    )
    parser.add_argument(
        "--start",
        "-s",
        type=str,
        default=None,
        help="Start location name to check hotspot status (e.g. 'Jubilee Hills' or new location 'Alwal')",
    )
    parser.add_argument(
        "--end",
        "-e",
        type=str,
        default=None,
        help="End location name to check hotspot status (e.g. 'Bachupally' or new location 'Secunderabad')",
    )
    parser.add_argument(
        "--start_lat",
        type=float,
        default=None,
        help="Optional start latitude coordinate",
    )
    parser.add_argument(
        "--start_lng",
        type=float,
        default=None,
        help="Optional start longitude coordinate",
    )
    parser.add_argument(
        "--end_lat",
        type=float,
        default=None,
        help="Optional destination latitude coordinate",
    )
    parser.add_argument(
        "--end_lng",
        type=float,
        default=None,
        help="Optional destination longitude coordinate",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train / re-train the ML Hotspot prediction model from the CSV dataset",
    )
    parser.add_argument(
        "--top",
        "-t",
        type=int,
        default=20,
        help="Number of top accident hotspots to display from historical dataset (default: 20)",
    )
    args = parser.parse_args()

    # Re-train model if requested
    if args.train:
        train_hotspot_model()
        print("\nModel training complete.")
        return

    # If start and end locations are passed, evaluate that route (historical or ML-predicted new route)
    if args.start and args.end:
        print(f"\nEvaluating Hotspot Status for Route: {args.start} -> {args.end}\n")
        result = detect_hotspot(
            start_location=args.start,
            end_location=args.end,
            start_latitude=args.start_lat,
            start_longitude=args.start_lng,
            end_latitude=args.end_lat,
            end_longitude=args.end_lng,
        )

        if result.get("is_new_route"):
            print("--- ML Model Prediction (New Route) ---")
            print(f"Status: {'IDENTIFIED ACCIDENT HOTSPOT' if result['is_hotspot'] else 'NORMAL FLOW CORRIDOR'}")
            print(f"Route: {result['start_location']} -> {result['end_location']}")
            print(f"Hotspot Probability: {result.get('hotspot_probability', 0.0)}%")
            print(f"Predicted Accident Risk: {result['predicted_risk']}%")
            print(f"Risk Classification: {result['risk']}")
            print(f"Estimated Corridor Distance: {result.get('distance_km', 'N/A')} km")
            if result.get("contributing_factors"):
                print("Risk Contributing Factors:")
                for factor in result["contributing_factors"]:
                    print(f"  • {factor}")
        else:
            print("--- Historical Empirical Record ---")
            print(f"Status: Identified Accident Hotspot (Rank #{result['hotspot_id']})")
            print(f"Matched Route: {result['start_location']} -> {result['end_location']}")
            print(f"Total Recorded Accidents: {result['accidents']}")
            print(f"Risk Level: {result['risk']}")
            print(f"Historical Average Risk: {result['average_risk']}%")
            print(f"Distance: {result.get('distance_km', 'N/A')} km")
            print(f"Coordinates: [{result['start_latitude']}, {result['start_longitude']}] -> [{result['end_latitude']}, {result['end_longitude']}]")

        print("\nSummary Message:")
        print(result["message"])
        return

    # Otherwise run batch detection across all historical routes
    print("\nRunning Accident Hotspot Analysis across Hyderabad Routes...\n")
    hotspots = detect_all_hotspots(save_csv=True)

    print(f"\nTop {args.top} Accident Hotspots (from Dataset)\n")
    for _, row in hotspots.head(args.top).iterrows():
        print(f"Accident Hotspot #{row['hotspot_id']}")
        print(f"Route: {row['start_location']} -> {row['end_location']}")
        print(f"Accidents: {row['accidents']}")
        print(f"Risk: {row['risk']}")
        print(f"Average Risk: {row['average_risk']:.2f}%")
        print("-" * 40)


if __name__ == "__main__":
    main()
