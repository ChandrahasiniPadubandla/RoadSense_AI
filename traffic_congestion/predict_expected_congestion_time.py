import os
import joblib
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from datetime import datetime, timedelta

# Compatibility shim for scikit-learn models pickled across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load model
time_regressor = XGBRegressor()
time_regressor.load_model(os.path.join(BASE_DIR, "expected_congestion_time_regressor.json"))

# Load preprocessor
time_preprocessor = joblib.load(os.path.join(BASE_DIR, "expected_time_preprocessor.pkl"))


def predict_expected_congestion_time(new_data):

    # Convert input dictionary to DataFrame if needed
    if isinstance(new_data, pd.DataFrame):
        data = new_data
        hour_val = int(data["hour"].iloc[0])
    else:
        data = pd.DataFrame([new_data])
        hour_val = int(new_data["hour"])

    # Preprocess input
    data_processed = time_preprocessor.transform(data)

    # Predict congestion duration
    prediction = time_regressor.predict(data_processed)[0]

    expected_minutes = float(np.clip(prediction, 0, 120))

    # Resolve start time (support exact target_time or minute if provided)
    target_dt = new_data.get("target_time") if isinstance(new_data, dict) else None
    if isinstance(target_dt, datetime):
        start_time = target_dt
    else:
        minute_val = int(new_data.get("minute", 0)) if isinstance(new_data, dict) and "minute" in new_data else 0
        start_time = datetime(2000, 1, 1, hour_val, minute_val)

    # Add predicted congestion duration
    end_time = start_time + timedelta(minutes=expected_minutes)

    # Format times
    start_time_text = start_time.strftime("%I:%M %p").lstrip("0")
    end_time_text = end_time.strftime("%I:%M %p").lstrip("0")

    return {
        "expected_congestion_period": f"{start_time_text} - {end_time_text}",
        "duration_minutes": round(expected_minutes, 1)
    }