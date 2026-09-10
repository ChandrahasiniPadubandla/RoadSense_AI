from prediction.predict_traffic_congesion import predict_congestion


result = predict_congestion(
    road_id="LB-03",
    location="LB Nagar",
    latitude=17.3457,
    longitude=78.5522,
    road_type="Highway",
    hour=19,
    day_of_week="Friday",
    holiday=0,
    vehicle_count=580,
    average_speed=20,
    traffic_density=85,
    road_capacity=600,
    previous_traffic=560,
    weather="Rainy",
    rainfall=20,
    temperature=24,
    visibility=4,
    road_condition="Poor",
    historical_accidents=5
)


print("Predicted Congestion:", result["predicted_congestion"])
print("Expected Traffic Congestion:", result["expected_congestion_time"])