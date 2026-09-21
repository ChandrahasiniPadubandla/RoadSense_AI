import os
from datetime import datetime

import joblib
import pandas as pd
import xgboost as xgb

# Compatibility shim for scikit-learn models pickled across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList


# =========================================================
# 1. Find project folder
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# =========================================================
# 2. Model paths
# =========================================================

PREPROCESSOR_PATH = os.path.join(
    BASE_DIR,
    "model",
    "traffic_congestion_preprocessor (2).pkl"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "traffic_congestion_xgboost_model.json"
)
# =========================================================
# 3. Load preprocessor
# =========================================================
preprocessor = joblib.load(
    PREPROCESSOR_PATH
)
# =========================================================
# 4. Load XGBoost model
# =========================================================

model = xgb.XGBClassifier()

model.load_model(
    MODEL_PATH
)


# =========================================================
# 5. Traffic level mapping
# =========================================================
# Based on the training notebook:
#
# 0 -> LOW
# 1 -> MEDIUM
# 2 -> HIGH
# 3 -> SEVERE

LABEL_MAPPING = {
    0: "LOW",
    1: "MEDIUM",
    2: "HIGH",
    3: "SEVERE"
}


# =========================================================
# 6. Prediction function
# =========================================================

def predict_congestion(
    start_location,
    end_location,
    start_latitude,
    start_longitude,
    end_latitude,
    end_longitude,
    road_type,
    holiday,
    vehicle_count,
    average_speed,
    road_capacity,
    previous_traffic,
    weather,
    rainfall,
    temperature,
    visibility,
    road_condition
):

    # -----------------------------------------------------
    # Get current date and time automatically
    # -----------------------------------------------------

    current_time = datetime.now()

    hour = current_time.hour

    day_of_week = current_time.strftime("%A")

    timestamp_day = current_time.day

    timestamp_month = current_time.month

    timestamp_is_weekend = (
        1 if current_time.weekday() >= 5 else 0
    )

    is_peak_hour = (
        1
        if (7 <= hour <= 10 or 17 <= hour <= 21)
        else 0
    )


    # -----------------------------------------------------
    # Calculate traffic density
    # -----------------------------------------------------

    if road_capacity > 0:
        traffic_density = (
            vehicle_count / road_capacity
        )
    else:
        traffic_density = 0


    # -----------------------------------------------------
    # Create input data
    # -----------------------------------------------------

    input_data = {

        "start_location": start_location,
        "end_location": end_location,
        "start_latitude": start_latitude,
        "start_longitude": start_longitude,
        "end_latitude": end_latitude,
        "end_longitude": end_longitude,
        "road_type": road_type,
        "hour": hour,
        "holiday": holiday,
        "timestamp_day": timestamp_day,
        "timestamp_month": timestamp_month,
        "timestamp_is_weekend": timestamp_is_weekend,
        "is_peak_hour": is_peak_hour,
        "vehicle_count": vehicle_count,
        "average_speed": average_speed,
        "traffic_density": traffic_density,
        "road_capacity": road_capacity,

        "previous_traffic": previous_traffic,

        "day_of_week": day_of_week,

        "weather": weather,

        "rainfall": rainfall,

        "temperature": temperature,

        "visibility": visibility,

        "road_condition": road_condition
    }


    # -----------------------------------------------------
    # Convert input into DataFrame
    # -----------------------------------------------------

    input_df = pd.DataFrame(
        [input_data]
    )


    # -----------------------------------------------------
    # Apply trained preprocessing
    # -----------------------------------------------------

    processed_data = preprocessor.transform(
        input_df
    )


    # -----------------------------------------------------
    # Predict congestion class
    # -----------------------------------------------------

    prediction = model.predict(
        processed_data
    )[0]


    # -----------------------------------------------------
    # Convert number to traffic level
    # -----------------------------------------------------

    traffic_level = LABEL_MAPPING[
        int(prediction)
    ]


    # -----------------------------------------------------
    # Return result to backend
    # -----------------------------------------------------

    return traffic_level