import os
import joblib
import pandas as pd
import numpy as np
from xgboost import XGBClassifier, XGBRegressor

# Compatibility shim for scikit-learn models pickled across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------
# Load trained models and preprocessing files
# --------------------------------------------------

classifier = XGBClassifier()
classifier.load_model(os.path.join(BASE_DIR, "accident_risk_classifier.json"))

regressor = XGBRegressor()
regressor.load_model(os.path.join(BASE_DIR, "accident_risk_regressor.json"))

preprocessor = joblib.load(os.path.join(BASE_DIR, "accident_preprocessor.pkl"))
label_encoder = joblib.load(os.path.join(BASE_DIR, "accident_label_encoder.pkl"))


# --------------------------------------------------
# Prediction function
# --------------------------------------------------

def predict_accident_risk(new_data):

    # Convert input dictionary into DataFrame if needed
    if isinstance(new_data, pd.DataFrame):
        data = new_data
    else:
        data = pd.DataFrame([new_data])

    # Apply the same preprocessing used during training
    data_processed = preprocessor.transform(data)

    # ----------------------------------------------
    # Predict accident risk level and confidence
    # ----------------------------------------------

    level_prediction = classifier.predict(data_processed)

    risk_level = label_encoder.inverse_transform(
        level_prediction.astype(int)
    )[0]

    # Calculate classification confidence score
    probs = classifier.predict_proba(data_processed)[0]
    confidence_score = float(np.max(probs) * 100)

    # ----------------------------------------------
    # Predict accident risk percentage
    # ----------------------------------------------

    risk_prediction = regressor.predict(data_processed)[0]

    risk_percentage = float(np.clip(risk_prediction, 0, 100))

    # ----------------------------------------------
    # Return result
    # ----------------------------------------------

    return {
        "accident_risk": round(risk_percentage, 2),
        "accident_risk_level": risk_level,
        "confidence_score": round(confidence_score, 1),
        "probabilities": {cls: round(float(p), 4) for cls, p in zip(label_encoder.classes_, probs)}
    }


# --------------------------------------------------
# Test the prediction function
# --------------------------------------------------

if __name__ == "__main__":

    
    new_record = {

    "start_location": "Gachibowli",

    "end_location": "Hitech City",

    "start_latitude": 17.4401,

    "start_longitude": 78.3489,

    "end_latitude": 17.4483,

    "end_longitude": 78.3915,

    "road_type": "Arterial Road",

    "hour": 18,

    "day_of_week": "Friday",

    "holiday": 0,

    "vehicle_count": 1050,

    "average_speed": 32.5,

    "traffic_density": 75.0,

    "road_capacity": 1400,

    "previous_traffic": 1010,

    "weather": "Cloudy",

    "rainfall": 0.5,

    "temperature": 30.0,

    "visibility": 8.5,

    "road_condition": "Dry",

    "historical_accidents": 8,

    "congestion_level": "HIGH"
}

    result = predict_accident_risk(new_record)

    print("\nAccident Prediction Result")
    print("--------------------------")
    print("Accident Risk:", result["accident_risk"], "%")
    print("Risk Level:", result["accident_risk_level"])