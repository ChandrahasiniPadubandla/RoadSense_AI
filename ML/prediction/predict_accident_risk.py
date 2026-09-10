import joblib
import pandas as pd
from pathlib import Path


# Load the trained ML model
MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "accident_risk_model.pkl"

# Compatibility shim for scikit-learn models pickled across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList

bundle = joblib.load(MODEL_PATH)

model = bundle["model"]
label_encoder = bundle["label_encoder"]
features = bundle["features"]


def predict_record(new_record):
    """
    Predict accident risk level for a new road/traffic record.

    Input:
        new_record -> Python dictionary

    Output:
        prediction -> risk level
        probabilities -> probability of each risk level
    """

    # Convert dictionary into DataFrame
    new_data = pd.DataFrame([new_record])

    # Check for missing required features
    missing_features = [
        feature for feature in features
        if feature not in new_data.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    # Keep exactly the features used during model training
    new_data = new_data[features]

    # Predict encoded class
    prediction_encoded = model.predict(new_data)[0]

    # Convert encoded class back to risk label
    prediction_label = label_encoder.inverse_transform(
        [prediction_encoded]
    )[0]

    # Get probabilities
    probabilities_array = model.predict_proba(new_data)[0]

    # Get model class labels
    model_classes = model.classes_

    # Create readable probability dictionary
    probabilities = {}

    for class_value, probability in zip(
        model_classes,
        probabilities_array
    ):
        class_label = label_encoder.inverse_transform(
            [class_value]
        )[0]

        probabilities[str(class_label)] = round(
            float(probability),
            4
        )

    # Probability of predicted class
    predicted_probability = probabilities[str(prediction_label)]

    # Convert to percentage
    accident_risk = round(
        predicted_probability * 100,
        2
    )

    return {
        "accident_risk_level": str(prediction_label),
        "accident_risk": accident_risk,
        "probabilities": probabilities
    }