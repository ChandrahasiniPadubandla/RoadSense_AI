import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import joblib
import numpy as np

from src.config import settings
from src.ner_extractor import location_extractor
from src.prediction_client import prediction_client

GREETING_PATTERN = re.compile(
    r"^(?:(?:hi|hello|hey)(?:\s+(?:there|gm|good\s+(?:morning|mrng)))?"
    r"|gm|good\s+(?:morning|mrng|afternoon|evening))[!.? ]*$",
    re.IGNORECASE,
)
ROUTE_INTENT_CUES = (
    ("hotspot_query", re.compile(r"\b(?:hotspots?|blackspots?|accident[- ]prone)\b", re.I)),
    ("anomaly_query", re.compile(r"\b(?:anomal(?:y|ies)|unusual|abnormal|irregular)\b", re.I)),
    ("weather_prediction", re.compile(r"\b(?:weather|climate|rain|raining|temperature|humidity|wind|visibility)\b", re.I)),
    ("distance_query", re.compile(r"\b(?:distance|how\s+far)\b", re.I)),
    ("accident_prediction", re.compile(r"\b(?:accident|crash|collision|safety)\b", re.I)),
    ("traffic_prediction", re.compile(r"\b(?:traffic|congestion|traffic\s+jam|congested|travel\s+time|how\s+long|delay|eta|when\s+(?:will|do|can)\s+i\s+(?:reach|arrive)|what\s+time\s+(?:will|do|can)\s+i\s+(?:reach|arrive)|routes?|directions?|drive|driving|navigate|navigation|way\s+to|how\s+to\s+(?:go|get|reach))\b", re.I)),
    ("accident_prediction", re.compile(r"\b(?:risk|risk\s+level|risk\s+percentage)\b", re.I)),
)
AREA_RANKING_QUERY_PATTERN = re.compile(
    r"\b(?:which|what|most|highest|high)\b.*\b(?:areas?|places?|locations?)\b",
    re.IGNORECASE,
)
AREA_LOOKUP_QUERY_PATTERN = re.compile(
    r"\b(?:where|which|what|show|list|find|tell\s+me)\b.*"
    r"\b(?:areas?|places?|locations?|zones?|roads?|streets?)\b",
    re.IGNORECASE,
)
AREA_LEVEL_PATTERN = re.compile(r"\b(?:high|medium|low|severe|sever)\b", re.IGNORECASE)


class ChatbotEngine:
    """
    Main Chatbot Intelligence Engine:
    1. Intent Classification using Retained Linear SVC (Calibrated) Model
    2. spaCy NER & Regex Pattern Fallback Location Extraction (Start & End Locations)
    3. Direct Backend API Dispatch (NO SIMULATED FALLBACKS)
    4. Displays Model Triggered, Start Location, End Location, and Exact Raw API Response
    """

    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR)
        self.vectorizer = None
        self.label_encoder = None
        self.active_model_name = "Linear SVC (Calibrated)"
        self.active_model = None
        self._pending_conversations: Dict[str, Dict[str, Any]] = {}
        self._load_artifacts()

    def _load_artifacts(self):
        vec_path = self.models_dir / "tfidf_vectorizer.pkl"
        le_path = self.models_dir / "label_encoder.pkl"
        best_path = self.models_dir / "best_model.pkl"
        svc_path = self.models_dir / "linear_svc_calibrated.pkl"

        if vec_path.exists():
            self.vectorizer = joblib.load(vec_path)
        if le_path.exists():
            self.label_encoder = joblib.load(le_path)

        if best_path.exists():
            self.active_model = joblib.load(best_path)
        elif svc_path.exists():
            self.active_model = joblib.load(svc_path)

    def list_available_models(self) -> List[Dict[str, Any]]:
        return [{
            "name": self.active_model_name,
            "is_active": True,
            "description": "Retained Calibrated Linear SVC Intent Classifier"
        }]

    def set_active_model(self, model_name: str) -> bool:
        return True

    def predict_intent(self, text: str) -> Dict[str, Any]:
        if not self.vectorizer or not self.active_model:
            self._load_artifacts()

        if not self.vectorizer or not self.active_model:
            return {"intent": "unknown", "confidence": 0.0, "probabilities": {}}

        vec = self.vectorizer.transform([text])
        classes = list(self.label_encoder.classes_)

        if hasattr(self.active_model, "predict_proba"):
            probs = self.active_model.predict_proba(vec)[0]
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])
            prob_dict = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
        elif hasattr(self.active_model, "decision_function"):
            df = self.active_model.decision_function(vec)[0]
            exp_df = np.exp(df - np.max(df))
            probs = exp_df / np.sum(exp_df)
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])
            prob_dict = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
        else:
            pred_idx = int(self.active_model.predict(vec)[0])
            confidence = 1.0
            prob_dict = {classes[pred_idx]: 1.0}

        predicted_intent = self.label_encoder.inverse_transform([pred_idx])[0]

        return {
            "intent": predicted_intent,
            "confidence": round(confidence, 4),
            "model_used": self.active_model_name,
            "probabilities": prob_dict
        }

    async def process_message(
        self,
        user_message: str,
        model_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes intent detection, location parsing, calls the live backend API directly (no fallbacks),
        and returns the exact API response alongside metadata.
        """
        greeting_match = GREETING_PATTERN.fullmatch(user_message.strip())
        if greeting_match:
            greeting = (
                "Good morning!"
                if re.search(
                    r"\b(?:gm|good\s+(?:morning|mrng))\b",
                    user_message.strip(),
                    re.IGNORECASE,
                )
                else "Hello!"
            )
            response_text = (
                f"{greeting} How can I help you with traffic predictions, "
                "accident risk, anomalies, hotspots, or weather?"
            )
            return {
                "query": user_message,
                "intent": "greeting",
                "confidence": 1.0,
                "model_triggered": None,
                "start_location": None,
                "end_location": None,
                "endpoint_called": None,
                "is_success": None,
                "api_response": {},
                "location_data": None,
                "response_text": response_text,
            }

        area_query_types = self._area_query_types(user_message)
        if area_query_types:
            return await self._process_area_status_query(
                user_message,
                area_query_types,
            )

        # 1. Intent Detection
        intent_data = self.predict_intent(user_message)
        confidence = intent_data["confidence"]

        # 2. Location Extraction (Start & End Locations)
        loc_data = location_extractor.extract(user_message)
        explicit_route_intent = self._explicit_route_intent(user_message)
        pending = (
            self._pending_conversations.get(conversation_id, {})
            if conversation_id
            else {}
        )
        pending_locations = pending.get("locations", [])
        current_locations = loc_data["locations"]

        if loc_data["is_corridor"]:
            locations = [loc_data["origin"], loc_data["destination"]]
        elif len(current_locations) >= 2:
            locations = current_locations[:2]
        elif current_locations:
            locations = list(dict.fromkeys(pending_locations + current_locations))
            if len(locations) > 2:
                locations = current_locations[:2]
        else:
            locations = pending_locations

        origin = locations[0] if len(locations) >= 2 else None
        dest = locations[1] if len(locations) >= 2 else None
        primary_loc = (
            dest
            or (locations[0] if locations else loc_data["primary_location"])
        )
        if len(locations) >= 2:
            loc_data.update(
                {
                    "locations": locations,
                    "origin": origin,
                    "destination": dest,
                    "primary_location": primary_loc,
                    "is_corridor": True,
                }
            )
        elif locations:
            loc_data.update(
                {
                    "locations": locations,
                    "origin": None,
                    "destination": None,
                    "primary_location": locations[0],
                    "is_corridor": False,
                }
            )

        intent = (
            "traffic_and_accident_prediction"
            if self._is_combined_traffic_accident_query(user_message)
            else explicit_route_intent or pending.get("intent")
        )
        target_time = self._extract_target_time(user_message)
        route_intents = {
            "traffic_prediction",
            "distance_query",
            "accident_prediction",
            "traffic_and_accident_prediction",
            "anomaly_query",
        }
        two_location_intents = {
            "traffic_prediction",
            "distance_query",
            "accident_prediction",
            "traffic_and_accident_prediction",
        }
        single_location_intents = {
            "anomaly_query",
            "hotspot_query",
            "weather_prediction",
        }
        if intent in two_location_intents:
            has_required_locations = bool(origin and dest)
        elif intent in single_location_intents:
            has_required_locations = bool(locations)
        else:
            has_required_locations = False

        if intent is None or not has_required_locations:
            if conversation_id:
                pending_state: Dict[str, Any] = {"locations": locations}
                if intent is not None:
                    pending_state["intent"] = intent
                self._pending_conversations[conversation_id] = pending_state

            if intent is None:
                if origin and dest:
                    map_url = f"{settings.LIVE_MAP_URL}?{urlencode({'start_location': origin, 'end_location': dest})}"
                    response_text = (
                        f"I found the route from {origin} to {dest}.\n\n"
                        f"[Open this route in the live map]({map_url})\n\n"
                        "What would you like to know about it: traffic, accident risk, "
                        "distance, anomalies, hotspots, or weather?"
                    )
                elif locations:
                    response_text = (
                        f"I found {locations[0]}. Please provide both a starting "
                        "location and destination, then tell me what you would like "
                        "to know: traffic, accident risk, distance, anomalies, "
                        "hotspots, or weather."
                    )
                else:
                    response_text = (
                        "What would you like to know: traffic, accident risk, distance, "
                        "anomalies, hotspots, or weather? Please include the location; "
                        "for route predictions, provide both a start and destination."
                    )
            elif intent in two_location_intents:
                service = {
                    "traffic_prediction": "traffic",
                    "distance_query": "distance",
                    "accident_prediction": "accident risk",
                }[intent]
                if locations:
                    response_text = (
                        f"I can check {service} for {locations[0]}. Please provide "
                        "the other location as well so I can identify the route."
                    )
                else:
                    response_text = (
                        f"I can check {service}. Please provide both the starting "
                        "location and destination (for example, 'Uppal to Nagole')."
                    )
            else:
                service = {
                    "anomaly_query": "anomalies",
                    "weather_prediction": "weather",
                    "hotspot_query": "hotspots",
                }[intent]
                response_text = (
                    f"I can check {service}. Please provide a location to continue."
                )

            clarification_map_url = None
            if origin and dest:
                clarification_map_url = f"{settings.LIVE_MAP_URL}?{urlencode({'start_location': origin, 'end_location': dest})}"

            return {
                "query": user_message,
                "intent": "clarification_required",
                "confidence": confidence,
                "model_triggered": None,
                "start_location": origin,
                "end_location": dest,
                "endpoint_called": None,
                "is_success": None,
                "api_response": {},
                "location_data": loc_data,
                "map_url": clarification_map_url,
                "response_text": response_text,
            }

        if conversation_id:
            self._pending_conversations.pop(conversation_id, None)

        location_error = None
        if intent in route_intents:
            known_locations = {
                location.casefold() for location in location_extractor.known_locations
            }
            location_fields = [
                (field, loc_data[field])
                for field in ("origin", "destination", "primary_location")
                if isinstance(loc_data[field], str)
                and loc_data[field] not in ("Hyderabad (General)",)
                and loc_data[field].casefold() not in known_locations
            ]
            locations_to_resolve = list(
                dict.fromkeys(location for _, location in location_fields)
            )
            if locations_to_resolve:
                resolution_results = await asyncio.gather(
                    *(
                        prediction_client.resolve_location(location)
                        for location in locations_to_resolve
                    )
                )
                resolved_locations = {}
                for location, result in zip(locations_to_resolve, resolution_results):
                    if not result.get("_is_success"):
                        location_error = result
                        break
                    resolved_locations[location] = result["location"]

                if location_error is None:
                    origin = resolved_locations.get(origin, origin)
                    dest = resolved_locations.get(dest, dest)
                    primary_loc = resolved_locations.get(primary_loc, primary_loc)
                    loc_data["origin"] = origin
                    loc_data["destination"] = dest
                    loc_data["primary_location"] = primary_loc
                    loc_data["locations"] = [
                        resolved_locations.get(location, location)
                        for location in loc_data["locations"]
                    ]

        if origin and dest:
            start_location = origin
            end_location = dest
        elif origin:
            start_location = origin
            end_location = primary_loc if primary_loc != origin else "Not specified"
        elif dest:
            start_location = "Current / User Origin"
            end_location = dest
        else:
            start_location = primary_loc if primary_loc != "Hyderabad (General)" else "General Area"
            end_location = "N/A (Single Location Query)"

        # 3. Model Triggered Mapping
        model_meta = {
            "traffic_prediction": {
                "name": "Traffic Prediction Model",
                "endpoint": "POST /predictions/traffic/route",
                "url": settings.traffic_route_url
            },
            "distance_query": {
                "name": "Route Distance",
                "endpoint": "POST /predictions/traffic/route",
                "url": settings.traffic_route_url
            },
            "accident_prediction": {
                "name": "Accident Risk Prediction Model",
                "endpoint": "POST /predictions/accidents/route",
                "url": settings.accident_route_url
            },
            "traffic_and_accident_prediction": {
                "name": "Traffic and Accident Risk Prediction Models",
                "endpoint": (
                    "POST /predictions/traffic/route and "
                    "POST /predictions/accidents/route"
                ),
                "url": (
                    f"{settings.traffic_route_url} and "
                    f"{settings.accident_route_url}"
                )
            },
            "anomaly_query": {
                "name": "Traffic Anomaly Detection Model (Isolation Forest)",
                "endpoint": "POST /anomalies/predict",
                "url": settings.anomalies_predict_url
            },
            "hotspot_query": {
                "name": "Accident Hotspots Analysis Model",
                "endpoint": "POST /hotspots/predict",
                "url": settings.hotspots_predict_url
            },
            "weather_prediction": {
                "name": "Weather Conditions API",
                "endpoint": f"GET/POST {settings.WEATHER_ENDPOINT}",
                "url": settings.weather_url
            }
        }

        meta = model_meta.get(intent, {
            "name": "Unknown Intent",
            "endpoint": "N/A",
            "url": "N/A"
        })
        model_triggered = f"{meta['name']} ({meta['endpoint']})"

        # 4. Strict Direct Call to Live API (NO MOCK FALLBACKS)
        api_data = {}
        if location_error is not None:
            api_data = location_error
        elif intent == "traffic_and_accident_prediction":
            traffic_request = (
                prediction_client.get_traffic_prediction(
                    origin, dest, primary_loc, target_time=target_time
                )
                if target_time
                else prediction_client.get_traffic_prediction(origin, dest, primary_loc)
            )
            traffic_result, accident_result = await asyncio.gather(
                traffic_request,
                prediction_client.get_accident_prediction(origin, dest, primary_loc),
            )
            api_data = {
                "_is_success": (
                    traffic_result.get("_is_success", False)
                    and accident_result.get("_is_success", False)
                ),
                "_endpoint": meta["url"],
                "traffic": traffic_result,
                "accident": accident_result,
            }
        elif intent in {"traffic_prediction", "distance_query"}:
            if target_time:
                api_data = await prediction_client.get_traffic_prediction(
                    origin, dest, primary_loc, target_time=target_time
                )
            else:
                api_data = await prediction_client.get_traffic_prediction(
                    origin, dest, primary_loc
                )
        elif intent == "accident_prediction":
            api_data = await prediction_client.get_accident_prediction(origin, dest, primary_loc)
        elif intent == "anomaly_query":
            if origin and dest:
                traffic_context = await prediction_client.get_traffic_prediction(
                    origin,
                    dest,
                    primary_loc,
                )
                anomaly_features, road_id = self._anomaly_features_from_traffic(
                    traffic_context
                )
                if traffic_context.get("_is_success") and "vehicle_count" in anomaly_features:
                    api_data = await prediction_client.get_anomaly_detection(
                        primary_loc,
                        road_id=road_id,
                        start_location=origin,
                        end_location=dest,
                        features=anomaly_features,
                    )
                else:
                    api_data = {
                        "_is_success": False,
                        "_endpoint": settings.anomalies_predict_url,
                        "error_message": (
                            "The traffic API did not provide a vehicle count, which is "
                            "required for anomaly detection."
                        ),
                        "traffic_context": traffic_context,
                    }
            else:
                road = await prediction_client.get_nearest_road(primary_loc)
                road_id = road.get("road_id") if road.get("_is_success") else None
                if isinstance(road_id, str):
                    api_data = await prediction_client.get_anomaly_detection(
                        primary_loc,
                        road_id=road_id,
                    )
                else:
                    api_data = {
                        "_is_success": False,
                        "_endpoint": settings.anomalies_predict_url,
                        "error_message": (
                            road.get("message")
                            or road.get("detail")
                            or road.get("error_message")
                            or "Could not find a monitored road for this location."
                        ),
                    }
        elif intent == "hotspot_query":
            api_data = await prediction_client.get_accident_hotspots(primary_loc)
        elif intent == "weather_prediction":
            api_data = await prediction_client.get_weather(primary_loc)

        # 5. Build Formatted Output displaying whatever the API returned
        is_success = api_data.get("_is_success", False) if isinstance(api_data, dict) else True
        endpoint_called = api_data.get("_endpoint", meta["url"]) if isinstance(api_data, dict) else meta["url"]

        # Clean display payload (hide internal underscore keys if present)
        clean_api_payload = {}
        if isinstance(api_data, dict):
            clean_api_payload = {k: v for k, v in api_data.items() if not k.startswith("_")}
            if intent == "traffic_and_accident_prediction":
                clean_api_payload = {
                    service: {
                        key: value
                        for key, value in result.items()
                        if not key.startswith("_")
                    }
                    for service, result in clean_api_payload.items()
                    if isinstance(result, dict)
                }
        else:
            clean_api_payload = api_data

        if intent == "traffic_and_accident_prediction":
            formatted_output = self._format_combined_traffic_accident_response(
                start_location,
                end_location,
                api_data["traffic"],
                api_data["accident"],
            )
        else:
            formatted_output = self._format_direct_response(
                model_triggered=model_triggered,
                start_loc=start_location,
                end_loc=end_location,
                endpoint_called=endpoint_called,
                confidence=confidence,
                is_success=is_success,
                api_payload=clean_api_payload,
                intent=intent,
            )

        map_url = None
        if origin and dest:
            map_url = f"{settings.LIVE_MAP_URL}?{urlencode({'start_location': origin, 'end_location': dest})}"
            formatted_output = (
                f"{formatted_output}\n\n"
                f"[Open this route in the live map]({map_url})"
            )

        return {
            "query": user_message,
            "intent": intent,
            "confidence": confidence,
            "model_triggered": model_triggered,
            "start_location": start_location,
            "end_location": end_location,
            "endpoint_called": endpoint_called,
            "is_success": is_success,
            "api_response": clean_api_payload,
            "location_data": loc_data,
            "map_url": map_url,
            "response_text": formatted_output
        }

    @staticmethod
    def _explicit_route_intent(message: str) -> Optional[str]:
        for intent, cue_pattern in ROUTE_INTENT_CUES:
            if cue_pattern.search(message):
                return intent

        fuzzy_cues = (
            ("hotspot_query", ("hotspot", "blackspot")),
            ("anomaly_query", ("anomaly", "unusual", "abnormal", "irregular")),
            ("weather_prediction", ("weather", "climate", "raining", "temperature", "humidity", "visibility")),
            ("distance_query", ("distance", "travel")),
            ("accident_prediction", ("accident", "collision", "safety")),
            ("traffic_prediction", ("traffic", "congestion", "congested", "route", "direction")),
        )
        words = re.findall(r"[a-z]+", message.casefold())
        for intent, cues in fuzzy_cues:
            if any(
                len(word) >= 5
                and SequenceMatcher(None, word, cue).ratio() >= 0.84
                for word in words
                for cue in cues
            ):
                return intent
        return None

    @staticmethod
    def _extract_target_time(message: str) -> Optional[str]:
        match = re.search(
            r"\b(?:in|after)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\b",
            message,
            re.IGNORECASE,
        )
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2).casefold()
        delay = timedelta(hours=amount) if unit.startswith(("hour", "hr")) else timedelta(minutes=amount)
        india_timezone = timezone(timedelta(hours=5, minutes=30))
        return (datetime.now(india_timezone) + delay).isoformat(timespec="seconds")

    @staticmethod
    def _area_query_types(message: str) -> List[str]:
        asks_for_areas = bool(
            AREA_RANKING_QUERY_PATTERN.search(message)
            or AREA_LOOKUP_QUERY_PATTERN.search(message)
        )
        if not asks_for_areas:
            return []

        words = re.findall(r"[a-z]+", message.casefold())
        query_types = []
        if re.search(r"\b(?:traffic|congestion|congested)\b", message, re.IGNORECASE) or any(
            SequenceMatcher(None, word, term).ratio() >= 0.82
            for word in words
            for term in ("traffic", "congestion", "congested")
        ):
            query_types.append("traffic")
        if re.search(r"\b(?:accidents?|crashes?|collisions?|hotspots?|blackspots?|risk)\b", message, re.IGNORECASE) or any(
            SequenceMatcher(None, word, term).ratio() >= 0.82
            for word in words
            for term in ("accident", "crash", "collision", "hotspot", "blackspot", "risk")
        ):
            query_types.append("accidents")
        return query_types

    @staticmethod
    def _requested_area_levels(message: str) -> List[str]:
        levels = []
        for match in AREA_LEVEL_PATTERN.finditer(message):
            level = match.group().upper()
            if level == "SEVER":
                level = "SEVERE"
            if level not in levels:
                levels.append(level)
        return levels or ["HIGH"]

    async def _process_area_status_query(
        self,
        message: str,
        query_types: List[str],
    ) -> Dict[str, Any]:
        requested_levels = self._requested_area_levels(message)
        traffic_response: Optional[Dict[str, Any]] = None
        hotspots_response: Optional[Dict[str, Any]] = None
        requests = []
        if "traffic" in query_types:
            requests.append(prediction_client.get_latest_traffic_predictions())
        if "accidents" in query_types:
            requests.append(prediction_client.get_latest_accident_hotspots())

        responses = await asyncio.gather(*requests)
        response_index = 0
        if "traffic" in query_types:
            traffic_response = responses[response_index]
            response_index += 1
        if "accidents" in query_types:
            hotspots_response = responses[response_index]

        traffic_ok = traffic_response is None or traffic_response.get("_is_success", False)
        hotspots_ok = hotspots_response is None or hotspots_response.get("_is_success", False)
        traffic_records = (
            traffic_response.get("data")
            if traffic_ok and traffic_response is not None
            else None
        )
        hotspot_records = (
            hotspots_response.get("data")
            if hotspots_ok and hotspots_response is not None
            else None
        )
        if traffic_ok and traffic_response is not None and not isinstance(traffic_records, list):
            traffic_ok = False
            traffic_records = None
            traffic_error = "The traffic latest endpoint returned an unexpected response."
        else:
            traffic_error = (
                None
                if traffic_ok
                else (traffic_response or {}).get("error_message", "Traffic lookup failed.")
            )
        if hotspots_ok and hotspots_response is not None and not isinstance(hotspot_records, list):
            hotspots_ok = False
            hotspot_records = None
            hotspots_error = "The accident hotspots endpoint returned an unexpected response."
        else:
            hotspots_error = (
                None
                if hotspots_ok
                else (hotspots_response or {}).get("error_message", "Accident area lookup failed.")
            )

        traffic_areas = (
            self._latest_area_records(
                traffic_records,
                requested_levels,
                level_fields=("congestion_level", "predicted_congestion"),
                timestamp_field="prediction_time",
                max_results=5,
            )
            if traffic_ok and traffic_records is not None
            else []
        )
        accident_areas = (
            self._latest_area_records(
                hotspot_records,
                requested_levels,
                level_fields=("risk_level",),
                timestamp_field="calculated_at",
                max_results=5,
            )
            if hotspots_ok and hotspot_records is not None
            else []
        )

        endpoint_urls = []
        if traffic_response is not None:
            endpoint_urls.append(traffic_response.get("_endpoint", settings.traffic_latest_url))
        if hotspots_response is not None:
            endpoint_urls.append(hotspots_response.get("_endpoint", settings.hotspots_list_url))

        api_response: Dict[str, Any] = {
            "requested_levels": requested_levels,
            "traffic_areas": traffic_areas,
            "accident_areas": accident_areas,
        }
        if traffic_error:
            api_response["traffic_error"] = traffic_error
        if hotspots_error:
            api_response["accident_error"] = hotspots_error

        response_sections = []
        if "traffic" in query_types:
            response_sections.append(
                self._format_area_records(
                    "Traffic",
                    traffic_areas,
                    requested_levels,
                    "prediction_time",
                    ("congestion_level", "predicted_congestion"),
                    traffic_error,
                )
            )
        if "accidents" in query_types:
            response_sections.append(
                self._format_area_records(
                    "Accident hotspots",
                    accident_areas,
                    requested_levels,
                    "calculated_at",
                    ("risk_level",),
                    hotspots_error,
                )
            )

        return {
            "query": message,
            "intent": "area_status_query",
            "confidence": 1.0,
            "model_triggered": "Latest database-backed area traffic and accident lookup",
            "start_location": None,
            "end_location": None,
            "endpoint_called": " and ".join(endpoint_urls),
            "is_success": traffic_ok and hotspots_ok,
            "api_response": api_response,
            "location_data": None,
            "response_text": "\n\n".join(response_sections),
        }

    @staticmethod
    def _latest_area_records(
        records: List[Any],
        requested_levels: List[str],
        level_fields: tuple[str, ...],
        timestamp_field: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        latest_by_area: Dict[str, Dict[str, Any]] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            if record.get("start_road_id") or record.get("end_road_id"):
                identity = "|".join(
                    str(record.get(key) or "")
                    for key in ("start_road_id", "end_road_id")
                )
            elif record.get("road_name"):
                identity = str(record["road_name"]).casefold().strip()
            elif record.get("zone_id"):
                identity = str(record["zone_id"])
            elif record.get("zone_name") or record.get("zone_label"):
                identity = str(record.get("zone_name") or record.get("zone_label")).casefold().strip()
            else:
                identity = "|".join(
                    str(record.get(key) or "").casefold().strip()
                    for key in ("start_location", "end_location")
                )
            if not identity.strip("|"):
                continue

            current = latest_by_area.get(identity)
            if current is None or ChatbotEngine._record_timestamp(record, timestamp_field) > (
                ChatbotEngine._record_timestamp(current, timestamp_field)
            ):
                latest_by_area[identity] = record

        selected = []
        for record in latest_by_area.values():
            level = next(
                (
                    value.strip().upper()
                    for field in level_fields
                    if isinstance((value := record.get(field)), str) and value.strip()
                ),
                None,
            )
            if level in requested_levels:
                selected.append(record)
        selected.sort(
            key=lambda record: ChatbotEngine._record_timestamp(record, timestamp_field),
            reverse=True,
        )
        return selected[:max_results]

    @staticmethod
    def _record_timestamp(record: Dict[str, Any], field: str) -> float:
        value = record.get(field)
        if not isinstance(value, str):
            return 0.0
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp.timestamp()
        except ValueError:
            return 0.0

    @staticmethod
    def _format_area_records(
        title: str,
        records: List[Dict[str, Any]],
        requested_levels: List[str],
        timestamp_field: str,
        level_fields: tuple[str, ...],
        error: Optional[str],
    ) -> str:
        levels_label = ", ".join(requested_levels)
        if error:
            return f"{title} lookup failed: {error}"
        if not records:
            return f"Latest {title.lower()} at {levels_label}: no matching records found."

        lines = [f"Latest {title.lower()} at {levels_label} level:"]
        for record in records:
            area = (
                record.get("zone_name")
                or record.get("zone_label")
                or record.get("road_name")
                or "Unknown area"
            )
            if area == "Unknown area":
                endpoints = [
                    record.get("start_location"),
                    record.get("end_location"),
                ]
                area = " to ".join(value for value in endpoints if isinstance(value, str) and value)
                area = area or "Unknown area"
            level = next(
                (
                    record[field]
                    for field in level_fields
                    if isinstance(record.get(field), str) and record[field].strip()
                ),
                "Unknown",
            )
            timestamp = record.get(timestamp_field)
            details = [str(area), f"backend risk level {str(level).upper()}"]
            if isinstance(record.get("risk_score"), (int, float)):
                details.append(f"risk score {record['risk_score']}")
            if isinstance(record.get("accident_count"), int):
                details.append(
                    f"{record['accident_count']} historical accidents (context)"
                )
            if isinstance(timestamp, str) and timestamp:
                details.append(f"updated {timestamp}")
            lines.append("- " + " — ".join(details))
        return "\n".join(lines)

    @staticmethod
    def _is_combined_traffic_accident_query(message: str) -> bool:
        has_traffic = re.search(
            r"\b(?:traffic|congestion|congested|busy|jam)\b",
            message,
            re.IGNORECASE,
        )
        has_accident = re.search(
            r"\b(?:accidents?|crashes?|collisions?|accident\s+risk)\b",
            message,
            re.IGNORECASE,
        )
        return bool(has_traffic and has_accident)

    def _format_combined_traffic_accident_response(
        self,
        start_loc: str,
        end_loc: str,
        traffic_result: Dict[str, Any],
        accident_result: Dict[str, Any],
    ) -> str:
        lines = [f"Start location: {start_loc}", f"End location: {end_loc}"]

        for service, result, fields in (
            (
                "Traffic",
                traffic_result,
                (
                    ("Distance", ("distance_km", "distance", "route_distance_km")),
                    ("Congestion level", ("congestion_level",)),
                    ("Estimated time", ("estimated_time", "travel_time", "estimated_duration")),
                ),
            ),
            (
                "Accident risk",
                accident_result,
                (
                    ("Risk percentage", ("risk_percentage", "accident_risk_percentage")),
                    ("Risk level", ("risk_level", "accident_risk_level")),
                    (
                        "Historical accidents count",
                        ("historical_accidents_count", "historical_accidents", "accident_count"),
                    ),
                ),
            ),
        ):
            if not result.get("_is_success"):
                error = (
                    result.get("error_message")
                    or result.get("message")
                    or result.get("detail")
                    or "The backend API request was unsuccessful."
                )
                lines.append(f"{service} request failed: {error}")
                continue

            lines.append(f"{service}:")
            for label, keys in fields:
                value = self._first_response_value(result, keys)
                if value is not None:
                    lines.append(f"{label}: {value}")

        return "\n".join(lines)

    @staticmethod
    def _anomaly_features_from_traffic(
        traffic_response: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Optional[str]]:
        feature_bundle = traffic_response.get("ml_features")
        if not isinstance(feature_bundle, dict):
            feature_bundle = {}

        previous_records = traffic_response.get("previous_records")
        if not isinstance(previous_records, dict):
            previous_records = feature_bundle.get("previous_records")
        if not isinstance(previous_records, dict):
            previous_records = {}

        road_conditions = traffic_response.get("road_conditions")
        if not isinstance(road_conditions, dict):
            road_conditions = feature_bundle.get("road_conditions")
        if not isinstance(road_conditions, dict):
            road_conditions = {}

        temporal_data = feature_bundle.get("temporal_data")
        if not isinstance(temporal_data, dict):
            temporal_data = {}

        features: Dict[str, Any] = {}
        for key in ("vehicle_count", "average_speed", "traffic_density", "historical_accidents"):
            if key in previous_records:
                features[key] = previous_records[key]
        if "road_capacity" in road_conditions:
            features["road_capacity"] = road_conditions["road_capacity"]
        if "hour" in temporal_data:
            features["hour"] = temporal_data["hour"]

        route_data = feature_bundle.get("route")
        if not isinstance(route_data, dict):
            route_data = {}
        road_id = route_data.get("road_id") or traffic_response.get("start_road_id")
        return features, road_id if isinstance(road_id, str) else None

    def _format_direct_response(
        self,
        model_triggered: str,
        start_loc: str,
        end_loc: str,
        endpoint_called: str,
        confidence: float,
        is_success: bool,
        api_payload: Any,
        intent: str,
    ) -> str:
        if not is_success:
            error = None
            if isinstance(api_payload, dict):
                error = (
                    api_payload.get("error_message")
                    or api_payload.get("message")
                    or api_payload.get("detail")
                )
            return f"Prediction request failed: {error or 'The backend API request was unsuccessful.'}"

        if intent == "anomaly_query":
            prediction = self._first_response_value(
                api_payload,
                ("prediction", "anomaly_status"),
            )
            is_anomaly = self._first_response_value(api_payload, ("is_anomaly",))
            confidence_score = self._first_response_value(
                api_payload,
                ("confidence_score", "confidence"),
            )
            road_name = self._first_response_value(api_payload, ("road_name",))
            anomaly_score = self._first_response_value(api_payload, ("anomaly_score",))
            features = api_payload.get("features_used")
            if not isinstance(features, dict):
                features = {}

            lines = [
                f"Start location: {start_loc}",
                f"End location: {end_loc}",
                f"Anomaly prediction: {prediction or 'Not provided by API'}",
            ]
            if isinstance(is_anomaly, bool):
                lines.append(
                    f"Anomaly detected: {'Yes' if is_anomaly else 'No'}"
                )
            if anomaly_score is not None:
                lines.append(f"Anomaly score: {anomaly_score}")
            if confidence_score is not None:
                lines.append(f"Confidence: {confidence_score}%")
            if road_name is not None:
                lines.append(f"Road: {road_name}")

            feature_labels = (
                ("vehicle_count", "Vehicle count"),
                ("average_speed", "Average speed"),
                ("traffic_density", "Traffic density"),
                ("road_capacity", "Road capacity"),
                ("previous_traffic", "Previous traffic"),
                ("hour", "Hour"),
                ("historical_accidents", "Historical accidents"),
            )
            available_features = [
                (label, features[key])
                for key, label in feature_labels
                if key in features
            ]
            if available_features:
                lines.append("Conditions used:")
                lines.extend(
                    f"{label}: {value}" for label, value in available_features
                )
            return "\n".join(lines)

        if intent == "distance_query":
            fields = (
                ("Distance", ("distance_km", "distance", "route_distance_km")),
            )
        elif intent == "accident_prediction":
            fields = (
                ("Start location", ("start_location", "origin")),
                ("End location", ("end_location", "destination")),
                ("Distance", ("distance_km", "distance", "route_distance_km")),
                ("Risk percentage", ("risk_percentage", "accident_risk_percentage")),
                ("Risk level", ("risk_level", "accident_risk_level")),
                (
                    "Historical accidents count",
                    ("historical_accidents_count", "historical_accidents", "accident_count"),
                ),
            )
        elif intent == "traffic_prediction":
            fields = (
                ("Start location", ("start_location", "origin")),
                ("End location", ("end_location", "destination")),
                ("Distance", ("distance_km", "distance", "route_distance_km")),
                ("Congestion level", ("congestion_level",)),
                ("Estimated time", ("estimated_time", "travel_time", "estimated_duration")),
            )
        elif intent == "weather_prediction":
            fields = (
                ("Weather condition", ("weather_condition", "condition", "weather")),
                ("Temperature", ("temperature",)),
                ("Rainfall", ("rainfall",)),
                ("Humidity", ("humidity",)),
                ("Visibility", ("visibility",)),
                ("Wind speed", ("wind_speed",)),
                ("Live data", ("is_live",)),
                ("Source", ("source",)),
                ("Updated at", ("timestamp",)),
            )
        else:
            status_text = "🟢 HTTP SUCCESS" if is_success else "🔴 API CALL FAILED / UNREACHABLE"
            json_output = json.dumps(api_payload, indent=2, ensure_ascii=False)
            return "\n".join(
                (
                    f"🤖 MODEL TRIGGERED : {model_triggered}",
                    f"📍 START LOCATION  : {start_loc}",
                    f"🏁 END LOCATION    : {end_loc}",
                    f"📡 ENDPOINT CALLED : {endpoint_called}",
                    f"⚡ STATUS          : {status_text} (Intent Confidence: {confidence*100:.1f}%)",
                    f"\n📦 EXACT API RESPONSE:",
                    f"```json\n{json_output}\n```",
                )
            )

        lines = []
        for label, keys in fields:
            value = self._first_response_value(api_payload, keys)
            if label == "Start location" and value is None:
                value = start_loc
            elif label == "End location" and value is None:
                value = end_loc
            elif label == "Live data" and isinstance(value, bool):
                value = "Yes" if value else "No"
            if value is None:
                value = "Not provided by API"
            lines.append(f"{label}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _first_response_value(payload: Any, keys: tuple[str, ...]) -> Any:
        if not isinstance(payload, dict):
            return None
        for key in keys:
            value = payload.get(key)
            if value is not None and value != "":
                return value
        return None

chatbot_engine = ChatbotEngine()
