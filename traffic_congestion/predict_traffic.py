import os
import joblib
import pandas as pd
from xgboost import XGBClassifier

# Compatibility shim for scikit-learn models pickled across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load the trained model
traffic_classifier = XGBClassifier()
traffic_classifier.load_model(
    os.path.join(BASE_DIR, "traffic_congestion_classifier.json")
)

# Load preprocessing and label encoder
traffic_preprocessor = joblib.load(
    os.path.join(BASE_DIR, "traffic_preprocessor.pkl")
)

traffic_label_encoder = joblib.load(
    os.path.join(BASE_DIR, "traffic_label_encoder.pkl")
)


def predict_traffic(new_data):

    # Convert input dictionary into DataFrame if needed
    if isinstance(new_data, pd.DataFrame):
        data = new_data
    else:
        data = pd.DataFrame([new_data])

    # Preprocess input data
    data_processed = traffic_preprocessor.transform(data)

    # Predict congestion level
    prediction = traffic_classifier.predict(data_processed)

    # Convert prediction number back to text
    congestion_level = traffic_label_encoder.inverse_transform(
        prediction.astype(int)
    )[0]

    # Calculate model confidence score
    confidence_score = None
    try:
        probs = traffic_classifier.predict_proba(data_processed)[0]
        confidence_score = round(float(max(probs)) * 100.0, 1)
    except Exception:
        confidence_score = None

    return {
        "congestion_level": congestion_level,
        "confidence_score": confidence_score
    }