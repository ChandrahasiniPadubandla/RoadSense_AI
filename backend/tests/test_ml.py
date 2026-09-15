import unittest

from pydantic import ValidationError

from app.routers.ml import predict_anomaly, predict_congestion
from app.schemas.ml import AnomalyPredictionRequest, CongestionPredictionRequest


class MLIntegrationTests(unittest.TestCase):
    def test_congestion_prediction_uses_deterministic_mock(self):
        request = CongestionPredictionRequest(
            road_id="ROAD-001",
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
            historical_accidents=5,
        )

        response = predict_congestion(request)

        self.assertEqual(response.predicted_congestion, "SEVERE")
        self.assertEqual(response.expected_congestion_time, "7:00 PM - 8:00 PM")
        self.assertEqual(response.model_status, "mock")

    def test_anomaly_prediction_detects_capacity_overload(self):
        request = AnomalyPredictionRequest(
            vehicle_count=601,
            average_speed=10,
            traffic_density=82,
            road_capacity=600,
            previous_traffic=580,
        )

        response = predict_anomaly(request)

        self.assertEqual(response.prediction, "ANOMALY")
        self.assertEqual(response.model_status, "mock")

    def test_invalid_congestion_request_is_rejected(self):
        with self.assertRaises(ValidationError):
            CongestionPredictionRequest(
                road_id="ROAD-001",
                location="LB Nagar",
                latitude=100,
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
                historical_accidents=5,
            )


if __name__ == "__main__":
    unittest.main()
