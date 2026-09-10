from prediction.predict_accident_risk import predict_record


new_record = {
    "location": "Uppal Road",
    "latitude": 17.405,
    "longitude": 78.559,
    "road_type": "HIGHWAY",
    "hour": 8,
    "day_of_week": "SUNDAY",
    "holiday": 1,
    "vehicle_count": 473,
    "average_speed": 43.8,
    "traffic_density": 59.1,
    "road_capacity": 800,
    "previous_traffic": 424,
    "weather": "CLEAR",
    "rainfall": 0,
    "temperature": 27.7,
    "visibility": 10,
    "road_condition": "GOOD",
    "historical_accidents": 20,
    "congestion_level": "HIGH"
}


result = predict_record(new_record)

print("Prediction Result:")
print("------------------")
print("Accident Risk Level:", result["accident_risk_level"])
print("Accident Risk:", result["accident_risk"], "%")
print("Probabilities:", result["probabilities"])