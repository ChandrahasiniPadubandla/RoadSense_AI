import joblib
import pandas as pd


# Load model and scaler
model = joblib.load("model/traffic_anomaly_isolation_forest.pkl")
scaler = joblib.load("model/traffic_anomaly_scaler.pkl")


def predict_anomaly(
    vehicle_count,
    average_speed,
    traffic_density,
    road_capacity,
    previous_traffic
):

    # Create input DataFrame
    new_traffic = pd.DataFrame({
        "vehicle_count": [vehicle_count],
        "average_speed": [average_speed],
        "traffic_density": [traffic_density],
        "road_capacity": [road_capacity],
        "previous_traffic": [previous_traffic]
    })

    # Scale input
    scaled_data = scaler.transform(new_traffic)

    # Prediction
    prediction = model.predict(scaled_data)

    # Convert model output
    if prediction[0] == -1:
        return "ANOMALY"
    else:
        return "NORMAL"