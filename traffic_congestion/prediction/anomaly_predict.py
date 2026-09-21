import os
import joblib
import pandas as pd


# --------------------------------------------------
# 1. Find project folder
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# --------------------------------------------------
# 2. Model paths
# --------------------------------------------------

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "final_traffic_anomaly_model.pkl"
)

SCALER_PATH = os.path.join(
    BASE_DIR,
    "model",
    "traffic_anomaly_scaler.pkl"
)

FEATURES_PATH = os.path.join(
    BASE_DIR,
    "model",
    "traffic_anomaly_features.pkl"
)


# --------------------------------------------------
# 3. Load saved ML artifacts
# --------------------------------------------------

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
features = joblib.load(FEATURES_PATH)


# --------------------------------------------------
# 4. Anomaly Prediction Function
# --------------------------------------------------

def predict_anomaly(
    vehicle_count,
    average_speed,
    traffic_density,
    road_capacity,
    previous_traffic,
    hour
):

    # Create input data
    input_data = {
        "vehicle_count": vehicle_count,
        "average_speed": average_speed,
        "traffic_density": traffic_density,
        "road_capacity": road_capacity,
        "previous_traffic": previous_traffic,
        "hour": hour
    }

    # Convert input to DataFrame
    input_df = pd.DataFrame([input_data])

    # Arrange features in the same order used during training
    input_df = input_df[features]

    # Apply the saved scaler
    input_scaled = scaler.transform(input_df)

    # Make prediction
    prediction = model.predict(input_scaled)[0]

    # Isolation Forest:
    # 1  = Normal
    # -1 = Anomaly

    if prediction == -1:
        return "ANOMALY"
    else:
        return "NORMAL"