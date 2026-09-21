from predict_expected_congestion_time import predict_expected_congestion_time
from predict_traffic import predict_traffic
from predict_anomaly import predict_anomaly, predict_anomaly_detailed

new_record = {
    "start_location": "Secunderabad",
    "end_location": "Paradise",
    "start_latitude": 27.6001,
    "start_longitude": 67.5678,
    "end_latitude": 37.4657,
    "end_longitude": 98.4566,
    "road_type": "Arterial Road",
    "hour": 23,
    "day_of_week": "Tuesday",
    "holiday": 0,
    "vehicle_count": 980,
    "average_speed": 24.75,
    "traffic_density": 95,
    "road_capacity": 1400,
    "previous_traffic": 910,
    "weather": "Cloudy",
    "rainfall": 1.5,
    "temperature": 27,
    "visibility": 7.20,
    "road_condition": "Slightly Wet",
    "historical_accidents": 11
}

result_time = predict_expected_congestion_time(new_record)
print("Expected Congestion Period:", result_time["expected_congestion_period"])

result_traffic = predict_traffic(new_record)
print("Traffic Congestion Level:", result_traffic["congestion_level"])

result_anomaly = predict_anomaly_detailed(new_record)
print("Traffic Anomaly Detection:", result_anomaly["prediction"], f"(score: {result_anomaly['anomaly_score']})")