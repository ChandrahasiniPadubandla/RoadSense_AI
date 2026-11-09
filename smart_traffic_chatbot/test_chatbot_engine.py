import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.chatbot_engine import ChatbotEngine
from src.prediction_client import PredictionServiceClient


def route_data() -> dict[str, object]:
    return {
        "locations": ["Uppal", "Nagole"],
        "origin": "Uppal",
        "destination": "Nagole",
        "primary_location": "Nagole",
        "is_corridor": True,
        "extraction_method": "test",
        "entities": [],
    }


class ChatbotEngineResponseTests(unittest.IsolatedAsyncioTestCase):
    def test_reach_route_with_followup_request_extracts_both_locations(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract("i want to reach bowenpally to tarnaka give me distance")

        self.assertEqual(result["origin"], "Bowenpally")
        self.assertEqual(result["destination"], "Tarnaka")
        self.assertTrue(result["is_corridor"])

    def test_from_route_with_followup_request_stops_at_destination(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract(
            "i want to go from boduppal to nagole give me distance"
        )

        self.assertEqual(result["origin"], "Boduppal")
        self.assertEqual(result["destination"], "Nagole")
        self.assertTrue(result["is_corridor"])

    def test_from_route_with_future_departure_stops_at_destination(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract(
            "what is the traffic condition from uppal to nagole "
            "if i start after 45 minutes"
        )

        self.assertEqual(result["origin"], "Uppal")
        self.assertEqual(result["destination"], "Nagole")
        self.assertEqual(result["locations"], ["Uppal", "Nagole"])
        self.assertTrue(result["is_corridor"])

    def test_route_written_as_origin_to_destination_preserves_order(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract("financial district to kothapet")

        self.assertEqual(result["origin"], "Financial District")
        self.assertEqual(result["destination"], "Kothapet")

    def test_locations_are_extracted_in_text_order_when_embedded_in_a_question(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        for text, origin, destination in (
            (
                "what is the traffic level from kukatpally to kompally",
                "Kukatpally",
                "Kompally",
            ),
            ("uppal to nagole what is traffic", "Uppal", "Nagole"),
            ("Uppal, what is traffic to Nagole", "Uppal", "Nagole"),
        ):
            with self.subTest(text=text):
                result = extractor.extract(text)
                self.assertEqual(result["origin"], origin)
                self.assertEqual(result["destination"], destination)

    def test_reach_destination_from_origin_extracts_correct_route(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract(
            "i want to reach nagole from uppal what is the traffic level"
        )

        self.assertEqual(result["origin"], "Uppal")
        self.assertEqual(result["destination"], "Nagole")

    def test_future_reach_query_extracts_route_and_traffic_intent(self) -> None:
        from src.ner_extractor import LocationExtractor

        message = (
            "i will start in 60mins from kachiguda to reach gamdipet "
            "so when will i reach"
        )
        result = LocationExtractor().extract(message)

        self.assertEqual(result["origin"], "Kachiguda")
        self.assertEqual(result["destination"], "Gandipet")
        self.assertEqual(
            ChatbotEngine._explicit_route_intent(message),
            "traffic_prediction",
        )

    async def test_future_reach_query_passes_target_time_to_traffic_prediction(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        message = (
            "i will start in 60mins from kachiguda to reach gamdipet "
            "so when will i reach"
        )
        before = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True, "estimated_time": "30 minutes"},
            ) as get_traffic,
        ):
            result = await engine.process_message(message)
        after = datetime.now(timezone(timedelta(hours=5, minutes=30)))

        self.assertEqual(result["intent"], "traffic_prediction")
        self.assertEqual(result["start_location"], "Kachiguda")
        self.assertEqual(result["end_location"], "Gandipet")
        get_traffic.assert_awaited_once()
        args, kwargs = get_traffic.await_args
        self.assertEqual(args, ("Kachiguda", "Gandipet", "Gandipet"))
        self.assertEqual(set(kwargs), {"target_time"})
        target_time = datetime.fromisoformat(kwargs["target_time"])
        self.assertGreaterEqual(target_time, before + timedelta(minutes=59))
        self.assertLessEqual(target_time, after + timedelta(minutes=61))

    async def test_traffic_client_sends_optional_target_time_in_payload(self) -> None:
        response = MagicMock(status_code=200)
        response.json.return_value = {"estimated_time": "30 minutes"}
        http_client = MagicMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=response)

        with patch(
            "src.prediction_client.httpx.AsyncClient",
            return_value=http_client,
        ):
            await PredictionServiceClient().get_traffic_prediction(
                "Kachiguda",
                "Gandipet",
                "Gandipet",
                target_time="2026-11-04T13:21:19+05:30",
            )

        http_client.post.assert_awaited_once()
        self.assertEqual(
            http_client.post.await_args.kwargs["json"],
            {
                "start_location": "Kachiguda",
                "end_location": "Gandipet",
                "persist": False,
                "target_time": "2026-11-04T13:21:19+05:30",
            },
        )

    def test_start_from_location_sets_route_origin_when_destination_is_first(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract(
            "what is the accident level at gachibowli if i start from balanagar"
        )

        self.assertEqual(result["origin"], "Balanagar")
        self.assertEqual(result["destination"], "Gachibowli")

    def test_area_traffic_question_does_not_extract_which_as_a_location(self) -> None:
        from src.ner_extractor import LocationExtractor

        extractor = LocationExtractor()
        result = extractor.extract("in which areas the traffic is high")

        self.assertEqual(result["locations"], [])
        self.assertIsNone(result["origin"])
        self.assertIsNone(result["destination"])

    async def test_area_traffic_question_uses_latest_database_records(self) -> None:
        engine = ChatbotEngine()
        with (
            patch.object(engine, "predict_intent") as predict_intent,
            patch(
                "src.chatbot_engine.location_extractor.extract"
            ) as extract_locations,
            patch(
                "src.chatbot_engine.prediction_client.get_latest_traffic_predictions",
                new_callable=AsyncMock,
                return_value={"_is_success": True, "data": []},
            ) as latest_traffic,
            patch(
                "src.chatbot_engine.prediction_client.get_latest_accident_hotspots",
                new_callable=AsyncMock,
            ) as latest_hotspots,
        ):
            for message in (
                "in which areas the traffic is high",
                "what are the most trafiic areas",
                "which areas have high traffic",
            ):
                with self.subTest(message=message):
                    result = await engine.process_message(message)
                    self.assertEqual(result["intent"], "area_status_query")
                    self.assertIn("Latest traffic at HIGH", result["response_text"])

            predict_intent.assert_not_called()
            extract_locations.assert_not_called()
            self.assertEqual(latest_traffic.await_count, 3)
            latest_hotspots.assert_not_awaited()

    async def test_combined_area_query_filters_latest_traffic_and_accident_levels(self) -> None:
        engine = ChatbotEngine()
        with (
            patch(
                "src.chatbot_engine.prediction_client.get_latest_traffic_predictions",
                new_callable=AsyncMock,
                return_value={
                    "_is_success": True,
                    "data": [
                        {
                            "road_name": "A Road",
                            "congestion_level": "HIGH",
                            "prediction_time": "2026-11-04T10:00:00",
                        },
                        {
                            "road_name": "A Road",
                            "congestion_level": "LOW",
                            "prediction_time": "2026-11-04T11:00:00",
                        },
                        {
                            "road_name": "B Road",
                            "congestion_level": "HIGH",
                            "prediction_time": "2026-11-04T10:30:00",
                        },
                    ],
                },
            ) as latest_traffic,
            patch(
                "src.chatbot_engine.prediction_client.get_latest_accident_hotspots",
                new_callable=AsyncMock,
                return_value={
                    "_is_success": True,
                    "data": [
                        {
                            "zone_name": "Central",
                            "risk_level": "HIGH",
                            "accident_count": 20,
                            "calculated_at": "2026-11-04T10:00:00",
                        },
                        {
                            "zone_name": "Central",
                            "risk_level": "SEVERE",
                            "accident_count": 21,
                            "calculated_at": "2026-11-04T11:00:00",
                        },
                    ],
                },
            ) as latest_hotspots,
        ):
            result = await engine.process_message(
                "where is high traffic and sever accident area in Hyderabad"
            )

        self.assertEqual(result["intent"], "area_status_query")
        self.assertEqual(result["api_response"]["requested_levels"], ["HIGH", "SEVERE"])
        self.assertEqual(
            [record["road_name"] for record in result["api_response"]["traffic_areas"]],
            ["B Road"],
        )
        self.assertEqual(
            [record["zone_name"] for record in result["api_response"]["accident_areas"]],
            ["Central"],
        )
        self.assertIn("backend risk level SEVERE", result["response_text"])
        self.assertIn("historical accidents (context)", result["response_text"])
        latest_traffic.assert_awaited_once_with()
        latest_hotspots.assert_awaited_once_with()

    def test_area_level_records_use_latest_record_before_level_filtering(self) -> None:
        records = [
            {"road_name": "Main Road", "congestion_level": "HIGH", "prediction_time": "2026-11-04T10:00:00"},
            {"road_name": "Main Road", "congestion_level": "MEDIUM", "prediction_time": "2026-11-04T11:00:00"},
        ]

        self.assertEqual(
            ChatbotEngine._latest_area_records(
                records,
                ["HIGH"],
                level_fields=("congestion_level",),
                timestamp_field="prediction_time",
                max_results=5,
            ),
            [],
        )

    async def test_route_without_service_asks_for_clarification(self) -> None:
        engine = ChatbotEngine()
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch("src.chatbot_engine.location_extractor.extract", return_value=route_data()),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
            ) as predict_traffic,
        ):
            for message in (
                "I want to go from Uppal to Nagole",
                "what is the direction from Ameerpet to Uppal",
            ):
                with self.subTest(message=message):
                    result = await engine.process_message(message)
                    self.assertEqual(result["intent"], "clarification_required")
                    self.assertIn("What would you like to know", result["response_text"])
                    self.assertIn(result["start_location"], result["response_text"])
                    self.assertIn(result["end_location"], result["response_text"])
        predict_traffic.assert_not_awaited()

    async def test_followup_service_uses_route_from_same_conversation(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        conversation_id = "route-followup-test"
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True},
            ) as get_traffic,
        ):
            clarification = await engine.process_message(
                "kukatpally to kompally",
                conversation_id=conversation_id,
            )
            result = await engine.process_message(
                "traffic",
                conversation_id=conversation_id,
            )

        self.assertEqual(clarification["intent"], "clarification_required")
        self.assertEqual(clarification["start_location"], "Kukatpally")
        self.assertEqual(clarification["end_location"], "Kompally")
        self.assertEqual(result["intent"], "traffic_prediction")
        self.assertEqual(result["start_location"], "Kukatpally")
        self.assertEqual(result["end_location"], "Kompally")
        get_traffic.assert_awaited_once_with(
            "Kukatpally",
            "Kompally",
            "Kompally",
        )

    async def test_partial_route_question_uses_route_after_service_clarification(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        conversation_id = "partial-route-followup-test"
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_accident_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True},
            ) as get_accident,
        ):
            prompt = await engine.process_message(
                "i want to go from uppal to nagole what is the",
                conversation_id=conversation_id,
            )
            result = await engine.process_message(
                "accident risk",
                conversation_id=conversation_id,
            )

        self.assertEqual(prompt["intent"], "clarification_required")
        self.assertEqual(prompt["start_location"], "Uppal")
        self.assertEqual(prompt["end_location"], "Nagole")
        self.assertEqual(result["intent"], "accident_prediction")
        get_accident.assert_awaited_once_with("Uppal", "Nagole", "Nagole")

    async def test_service_first_prompts_for_route_then_uses_it(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        conversation_id = "service-first-test"
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_accident_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True},
            ) as get_accident,
        ):
            prompt = await engine.process_message(
                "accident risk",
                conversation_id=conversation_id,
            )
            result = await engine.process_message(
                "Uppal to Nagole",
                conversation_id=conversation_id,
            )

        self.assertEqual(prompt["intent"], "clarification_required")
        self.assertIn("starting location and destination", prompt["response_text"])
        self.assertEqual(result["intent"], "accident_prediction")
        self.assertEqual(result["start_location"], "Uppal")
        self.assertEqual(result["end_location"], "Nagole")
        get_accident.assert_awaited_once_with("Uppal", "Nagole", "Nagole")

    async def test_service_then_separate_locations_uses_pending_request(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        conversation_id = "service-then-locations-test"
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "anomaly_query", "confidence": 0.5},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True},
            ) as get_traffic,
        ):
            prompt = await engine.process_message(
                "traffic",
                conversation_id=conversation_id,
            )
            first_location = await engine.process_message(
                "Uppal",
                conversation_id=conversation_id,
            )
            result = await engine.process_message(
                "Nagole",
                conversation_id=conversation_id,
            )

        self.assertEqual(prompt["intent"], "clarification_required")
        self.assertEqual(first_location["intent"], "clarification_required")
        self.assertEqual(result["intent"], "traffic_prediction")
        self.assertEqual(result["start_location"], "Uppal")
        self.assertEqual(result["end_location"], "Nagole")
        get_traffic.assert_awaited_once_with("Uppal", "Nagole", "Nagole")

    async def test_full_misspelled_traffic_request_uses_traffic_prediction(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True},
            ) as get_traffic,
        ):
            result = await engine.process_message(
                "i want to go from uppal to nagole what is the trafffic level"
            )

        self.assertEqual(result["intent"], "traffic_prediction")
        self.assertEqual(result["start_location"], "Uppal")
        self.assertEqual(result["end_location"], "Nagole")
        get_traffic.assert_awaited_once_with("Uppal", "Nagole", "Nagole")

    async def test_combined_traffic_and_accidents_query_calls_both_route_apis(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        traffic_response = {
            "_is_success": True,
            "distance_km": 30.48,
            "congestion_level": "MEDIUM",
            "estimated_time": "4:35 PM - 5:23 PM",
        }
        accident_response = {
            "_is_success": True,
            "risk_percentage": 24.5,
            "risk_level": "LOW",
            "historical_accidents_count": 0,
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "anomaly_query", "confidence": 0.7},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value=traffic_response,
            ) as get_traffic,
            patch(
                "src.chatbot_engine.prediction_client.get_accident_prediction",
                new_callable=AsyncMock,
                return_value=accident_response,
            ) as get_accident,
        ):
            result = await engine.process_message(
                "is there any traffic and accidents from kondapur to nagole"
            )

        self.assertEqual(result["intent"], "traffic_and_accident_prediction")
        self.assertTrue(result["is_success"])
        self.assertEqual(
            result["api_response"]["traffic"],
            {key: value for key, value in traffic_response.items() if not key.startswith("_")},
        )
        self.assertEqual(
            result["api_response"]["accident"],
            {key: value for key, value in accident_response.items() if not key.startswith("_")},
        )
        self.assertIn("Congestion level: MEDIUM", result["response_text"])
        self.assertIn("Risk level: LOW", result["response_text"])
        self.assertIn("Historical accidents count: 0", result["response_text"])
        get_traffic.assert_awaited_once_with("Kondapur", "Nagole", "Nagole")
        get_accident.assert_awaited_once_with("Kondapur", "Nagole", "Nagole")

    async def test_weather_from_route_uses_destination_not_extracted_sentence(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "weather_prediction", "confidence": 0.9},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                side_effect=extractor.extract,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_weather",
                new_callable=AsyncMock,
                return_value={"_is_success": True, "temperature": 25},
            ) as get_weather,
        ):
            result = await engine.process_message(
                "i want to reach nagole from uppal what is the weather condition"
            )

        self.assertEqual(result["intent"], "weather_prediction")
        self.assertEqual(result["start_location"], "Uppal")
        self.assertEqual(result["end_location"], "Nagole")
        get_weather.assert_awaited_once_with("Nagole")

    async def test_weather_response_is_formatted_without_json(self) -> None:
        engine = ChatbotEngine()
        weather_response = {
            "_is_success": True,
            "weather_condition": "Cloudy",
            "temperature": 28.3,
            "rainfall": 0.0,
            "humidity": 51.0,
            "visibility": 10.0,
            "wind_speed": 12.9,
            "is_live": True,
            "source": "Open-Meteo Live API",
            "timestamp": "2026-11-03T10:54:10.851445+00:00",
        }
        location_data = {
            "locations": ["Nagole"],
            "origin": None,
            "destination": None,
            "primary_location": "Nagole",
            "is_corridor": False,
            "extraction_method": "test",
            "entities": [],
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "weather_prediction", "confidence": 0.9},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                return_value=location_data,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_weather",
                new_callable=AsyncMock,
                return_value=weather_response,
            ),
        ):
            result = await engine.process_message("what is the weather in Nagole")

        self.assertIn("Weather condition: Cloudy", result["response_text"])
        self.assertIn("Temperature: 28.3", result["response_text"])
        self.assertIn("Rainfall: 0.0", result["response_text"])
        self.assertIn("Humidity: 51.0", result["response_text"])
        self.assertIn("Visibility: 10.0", result["response_text"])
        self.assertIn("Wind speed: 12.9", result["response_text"])
        self.assertIn("Live data: Yes", result["response_text"])
        self.assertIn("Source: Open-Meteo Live API", result["response_text"])
        self.assertIn("Updated at: 2026-11-03T10:54:10.851445+00:00", result["response_text"])
        self.assertNotIn("EXACT API RESPONSE", result["response_text"])
        self.assertNotIn("```json", result["response_text"])

    async def test_climate_query_uses_weather_prediction(self) -> None:
        from src.ner_extractor import LocationExtractor

        engine = ChatbotEngine()
        extractor = LocationExtractor()
        location_data = extractor.extract("what is the climate near Uppal")
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "hotspot_query", "confidence": 0.6},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                return_value=location_data,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_weather",
                new_callable=AsyncMock,
                return_value={
                    "_is_success": True,
                    "weather_condition": "Cloudy",
                    "temperature": 28.3,
                },
            ) as get_weather,
            patch(
                "src.chatbot_engine.prediction_client.get_accident_hotspots",
                new_callable=AsyncMock,
            ) as get_hotspots,
        ):
            result = await engine.process_message("what is the climate near Uppal")

        self.assertEqual(result["intent"], "weather_prediction")
        self.assertIn("Weather condition: Cloudy", result["response_text"])
        get_weather.assert_awaited_once_with("Uppal")
        get_hotspots.assert_not_awaited()

    async def test_bare_traffic_prompts_for_locations_instead_of_calling_general_area(self) -> None:
        engine = ChatbotEngine()
        location_data = {
            "locations": [],
            "origin": None,
            "destination": None,
            "primary_location": "Hyderabad (General)",
            "is_corridor": False,
            "extraction_method": "test",
            "entities": [],
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "anomaly_query", "confidence": 0.5},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                return_value=location_data,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
            ) as get_traffic,
            patch(
                "src.chatbot_engine.prediction_client.get_anomaly_detection",
                new_callable=AsyncMock,
            ) as get_anomaly,
        ):
            result = await engine.process_message("traffic")

        self.assertEqual(result["intent"], "clarification_required")
        self.assertIn("starting location and destination", result["response_text"])
        get_traffic.assert_not_awaited()
        get_anomaly.assert_not_awaited()

    async def test_unknown_route_locations_are_resolved_by_backend_search(self) -> None:
        engine = ChatbotEngine()
        unknown_route = {
            **route_data(),
            "locations": ["Cobalt Colony", "Lake View Enclave"],
            "origin": "Cobalt Colony",
            "destination": "Lake View Enclave",
            "primary_location": "Lake View Enclave",
        }

        async def resolve_location(location: str) -> dict[str, object]:
            return {
                "_is_success": True,
                "location": f"Resolved {location}",
            }

        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "distance_query", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                return_value=unknown_route,
            ),
            patch(
                "src.chatbot_engine.prediction_client.resolve_location",
                new_callable=AsyncMock,
                side_effect=resolve_location,
            ) as resolve,
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value={"_is_success": True, "distance_km": 10},
            ) as predict_traffic,
        ):
            result = await engine.process_message(
                "distance from Cobalt Colony to Lake View Enclave"
            )

        self.assertEqual(resolve.await_count, 2)
        predict_traffic.assert_awaited_once_with(
            "Resolved Cobalt Colony",
            "Resolved Lake View Enclave",
            "Resolved Lake View Enclave",
        )
        self.assertIn("Distance: 10", result["response_text"])

    async def test_greeting_does_not_run_intent_or_prediction_models(self) -> None:
        engine = ChatbotEngine()
        with (
            patch.object(engine, "predict_intent") as predict_intent,
            patch("src.chatbot_engine.location_extractor.extract") as extract_locations,
        ):
            for message, greeting in (
                ("hello", "Hello!"),
                ("hey", "Hello!"),
                ("good morning", "Good morning!"),
                ("good mrng", "Good morning!"),
                ("hello gm", "Good morning!"),
            ):
                with self.subTest(message=message):
                    result = await engine.process_message(message)
                    self.assertEqual(result["intent"], "greeting")
                    self.assertIn(greeting, result["response_text"])
                    for capability in (
                        "traffic predictions",
                        "accident risk",
                        "anomalies",
                        "hotspots",
                        "weather",
                    ):
                        self.assertIn(capability, result["response_text"])
            predict_intent.assert_not_called()
            extract_locations.assert_not_called()

    async def test_traffic_response_displays_only_traffic_fields(self) -> None:
        engine = ChatbotEngine()
        api_response = {
            "_is_success": True,
            "_endpoint": "http://localhost/predictions/traffic/route",
            "start_location": "Uppal",
            "end_location": "Nagole",
            "distance_km": 8.4,
            "risk_level": "MEDIUM",
            "congestion_level": "HIGH",
            "estimated_time": "25 minutes",
            "risk_percentage": 12,
            "historical_accidents_count": 3,
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "accident_prediction", "confidence": 0.8},
            ),
            patch("src.chatbot_engine.location_extractor.extract", return_value=route_data()),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value=api_response,
            ),
        ):
            result = await engine.process_message("traffic from Uppal to Nagole")

        self.assertEqual(result["intent"], "traffic_prediction")
        self.assertIn("Distance: 8.4", result["response_text"])
        self.assertIn("Congestion level: HIGH", result["response_text"])
        self.assertIn("Estimated time: 25 minutes", result["response_text"])
        self.assertNotIn("Risk:", result["response_text"])
        self.assertNotIn("Risk percentage", result["response_text"])
        self.assertNotIn("Historical accidents", result["response_text"])

    async def test_accident_response_displays_accident_fields(self) -> None:
        engine = ChatbotEngine()
        api_response = {
            "_is_success": True,
            "_endpoint": "http://localhost/predictions/accidents/route",
            "start_location": "Uppal",
            "end_location": "Nagole",
            "distance_km": 8.4,
            "risk_percentage": 14.5,
            "risk_level": "LOW",
            "historical_accidents_count": 2,
            "congestion_level": "HIGH",
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch("src.chatbot_engine.location_extractor.extract", return_value=route_data()),
            patch(
                "src.chatbot_engine.prediction_client.get_accident_prediction",
                new_callable=AsyncMock,
                return_value=api_response,
            ),
        ):
            result = await engine.process_message("accident risk from Uppal to Nagole")

        self.assertEqual(result["intent"], "accident_prediction")
        for field in ("Risk percentage: 14.5", "Risk level: LOW", "Historical accidents count: 2"):
            self.assertIn(field, result["response_text"])
        self.assertNotIn("Congestion level", result["response_text"])

    async def test_distance_query_displays_only_distance(self) -> None:
        engine = ChatbotEngine()
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "traffic_prediction", "confidence": 0.8},
            ),
            patch("src.chatbot_engine.location_extractor.extract", return_value=route_data()),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value={
                    "_is_success": True,
                    "_endpoint": "http://localhost/predictions/traffic/route",
                    "distance_km": 8.4,
                    "congestion_level": "HIGH",
                },
            ),
        ):
            result = await engine.process_message("distance from Uppal to Nagole")

        self.assertEqual(result["intent"], "distance_query")
        self.assertTrue(result["response_text"].startswith("Distance: 8.4"))
        self.assertEqual(
            result["map_url"],
            "http://localhost:5173/live-map?start_location=Uppal&end_location=Nagole",
        )
        self.assertIn(
            f"[Open this route in the live map]({result['map_url']})",
            result["response_text"],
        )

    async def test_route_anomaly_uses_traffic_features_before_prediction(self) -> None:
        engine = ChatbotEngine()
        traffic_context = {
            "_is_success": True,
            "start_road_id": "road-123",
            "ml_features": {
                "route": {"road_id": "road-123"},
                "road_conditions": {"road_capacity": 3100},
                "previous_records": {
                    "vehicle_count": 787,
                    "average_speed": 34.9,
                    "traffic_density": 46.2,
                    "historical_accidents": 0,
                },
                "temporal_data": {"hour": 15},
            },
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "anomaly_query", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                return_value=route_data(),
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_traffic_prediction",
                new_callable=AsyncMock,
                return_value=traffic_context,
            ) as get_traffic,
            patch(
                "src.chatbot_engine.prediction_client.get_anomaly_detection",
                new_callable=AsyncMock,
                return_value={
                    "_is_success": True,
                    "prediction": "NORMAL",
                    "is_anomaly": False,
                    "anomaly_score": 0.1478,
                    "confidence_score": 90.0,
                    "road_id": "road-123",
                    "road_name": "Kondapur Main Road",
                    "features_used": {
                        "vehicle_count": 783,
                        "average_speed": 37.77,
                        "traffic_density": 47.45,
                        "road_capacity": 3000,
                        "previous_traffic": 514,
                        "hour": 16,
                        "historical_accidents": 0,
                    },
                    "model_status": "trained-isolation-forest",
                },
            ) as get_anomaly,
        ):
            result = await engine.process_message("detect anomalies from Uppal to Nagole")

        get_traffic.assert_awaited_once_with("Uppal", "Nagole", "Nagole")
        get_anomaly.assert_awaited_once_with(
            "Nagole",
            road_id="road-123",
            start_location="Uppal",
            end_location="Nagole",
            features={
                "vehicle_count": 787,
                "average_speed": 34.9,
                "traffic_density": 46.2,
                "historical_accidents": 0,
                "road_capacity": 3100,
                "hour": 15,
            },
        )
        self.assertTrue(result["is_success"])
        self.assertIn("Anomaly prediction: NORMAL", result["response_text"])
        self.assertIn("Anomaly detected: No", result["response_text"])
        self.assertIn("Anomaly score: 0.1478", result["response_text"])
        self.assertIn("Confidence: 90.0%", result["response_text"])
        self.assertIn("Road: Kondapur Main Road", result["response_text"])
        self.assertIn("Vehicle count: 783", result["response_text"])
        self.assertIn("Historical accidents: 0", result["response_text"])
        self.assertNotIn("```json", result["response_text"])
        self.assertNotIn("EXACT API RESPONSE", result["response_text"])

    async def test_single_location_anomaly_resolves_road_id(self) -> None:
        engine = ChatbotEngine()
        location_data = {
            "locations": ["Ameerpet"],
            "origin": None,
            "destination": None,
            "primary_location": "Ameerpet",
            "is_corridor": False,
            "extraction_method": "test",
            "entities": [],
        }
        with (
            patch.object(
                engine,
                "predict_intent",
                return_value={"intent": "anomaly_query", "confidence": 0.8},
            ),
            patch(
                "src.chatbot_engine.location_extractor.extract",
                return_value=location_data,
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_nearest_road",
                new_callable=AsyncMock,
                return_value={"_is_success": True, "road_id": "road-456"},
            ),
            patch(
                "src.chatbot_engine.prediction_client.get_anomaly_detection",
                new_callable=AsyncMock,
                return_value={"_is_success": True, "prediction": "NORMAL"},
            ) as get_anomaly,
        ):
            result = await engine.process_message("detect anomalies near Ameerpet")

        get_anomaly.assert_awaited_once_with("Ameerpet", road_id="road-456")
        self.assertTrue(result["is_success"])


if __name__ == "__main__":
    unittest.main()
