import httpx
from typing import Dict, Any, Optional
from src.config import settings

class PredictionServiceClient:
    """
    Direct, strictly real-time HTTP client connecting to user's backend API endpoints:
    1. POST /predictions/traffic/route
    2. POST /predictions/accidents/route
    3. POST /anomalies/predict (Isolation Forest ML model)
    4. POST /hotspots/predict (Accident Hotspot Analysis)
    5. Weather API Route

    NO simulated fallbacks. Returns exactly what the live backend API returns.
    """

    def __init__(self):
        self.timeout = settings.HTTP_TIMEOUT_SECONDS

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        try:
            import os
            from uuid import UUID
            token = os.getenv("CHATBOT_INTERNAL_TOKEN")
            if not token:
                from app.security import create_access_token
                token = create_access_token(UUID("00000000-0000-0000-0000-000000000001"))
            if token:
                headers["Authorization"] = f"Bearer {token}"
        except Exception:
            pass
        return headers

    def _create_client(self) -> httpx.AsyncClient:
        try:
            from app.main import app
            transport = httpx.ASGITransport(app=app)
            return httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=self.timeout)
        except Exception:
            return httpx.AsyncClient(timeout=self.timeout)

    async def get_traffic_prediction(
        self,
        origin: Optional[str],
        destination: Optional[str],
        location: str,
        target_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = settings.traffic_route_url
        start_loc = origin or location
        end_loc = destination or location

        payload = {
            "start_location": start_loc,
            "end_location": end_loc,
            "persist": False,
        }
        if target_time:
            payload["target_time"] = target_time

        try:
            async with self._create_client() as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    async def get_accident_prediction(self, origin: Optional[str], destination: Optional[str], location: str, weather_info: Optional[Dict] = None) -> Dict[str, Any]:
        url = settings.accident_route_url
        start_loc = origin or location
        end_loc = destination or location

        payload = {
            "start_location": start_loc,
            "end_location": end_loc,
            "persist": False,
        }

        try:
            async with self._create_client() as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    async def resolve_location(self, location: str) -> Dict[str, Any]:
        url = f"{settings.BACKEND_BASE_URL.rstrip('/')}/geo/search"

        try:
            async with self._create_client() as client:
                response = await client.get(
                    url,
                    params={"query": location, "city": "Hyderabad", "limit": 5},
                )
                response.raise_for_status()
                places = response.json()
                if not isinstance(places, list):
                    return self._handle_error(
                        ValueError("The location search endpoint returned an unexpected response."),
                        url,
                    )

                place = next(
                    (
                        item
                        for item in places
                        if isinstance(item, dict)
                        and any(
                            isinstance(item.get(key), str)
                            and item[key].casefold().strip() == location.casefold().strip()
                            for key in ("primary_name", "name")
                        )
                    ),
                    None,
                )
                if place is None:
                    place = next(
                        (item for item in places if isinstance(item, dict)),
                        None,
                    )
                if place is None:
                    return self._handle_error(
                        ValueError(f"No map location was found for {location!r}."),
                        url,
                    )

                resolved_name = place.get("primary_name") or place.get("name")
                if not isinstance(resolved_name, str) or not resolved_name.strip():
                    return self._handle_error(
                        ValueError(f"The map search returned no name for {location!r}."),
                        url,
                    )

                return {
                    "_is_success": True,
                    "_endpoint": url,
                    "location": resolved_name,
                }
        except Exception as error:
            return self._handle_error(error, url)

    async def get_nearest_road(self, location: str) -> Dict[str, Any]:
        base_url = settings.BACKEND_BASE_URL.rstrip("/")
        search_url = f"{base_url}/geo/search"
        nearest_road_url = f"{base_url}/geo/nearest-road"

        try:
            async with self._create_client() as client:
                search_response = await client.get(
                    search_url,
                    params={"query": location, "city": "Hyderabad", "limit": 5},
                )
                search_response.raise_for_status()
                places = search_response.json()
                if not isinstance(places, list):
                    return self._handle_error(
                        ValueError("The location search endpoint returned an unexpected response."),
                        search_url,
                    )

                normalized_query = location.casefold().strip()
                place = next(
                    (
                        item
                        for item in places
                        if isinstance(item, dict)
                        and item.get("type") == "road"
                    ),
                    None,
                )
                if place is None:
                    place = next(
                        (
                            item
                            for item in places
                            if isinstance(item, dict)
                            and any(
                                isinstance(item.get(key), str)
                                and item[key].casefold().strip() == normalized_query
                                for key in ("primary_name", "name")
                            )
                        ),
                        None,
                    )
                if place is None:
                    place = next(
                        (item for item in places if isinstance(item, dict)),
                        None,
                    )
                if place is None:
                    return self._handle_error(
                        ValueError(f"No map location was found for {location!r}."),
                        search_url,
                    )

                latitude = place.get("latitude")
                longitude = place.get("longitude")
                if not isinstance(latitude, (int, float)) or not isinstance(
                    longitude, (int, float)
                ):
                    return self._handle_error(
                        ValueError(f"The map search returned no coordinates for {location!r}."),
                        search_url,
                    )

                road_response = await client.get(
                    nearest_road_url,
                    params={"lat": latitude, "lng": longitude},
                )
                return self._parse_response(road_response, nearest_road_url)
        except Exception as error:
            return self._handle_error(error, nearest_road_url)

    async def get_anomaly_detection(
        self,
        location: str,
        *,
        road_id: Optional[str] = None,
        start_location: Optional[str] = None,
        end_location: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = settings.anomalies_predict_url
        payload: Dict[str, Any] = {"persist": False}
        if road_id:
            payload["road_id"] = road_id
        if start_location:
            payload["start_location"] = start_location
        if end_location:
            payload["end_location"] = end_location
        if not road_id and not start_location and location:
            payload["start_location"] = location
        if features:
            for key in (
                "vehicle_count",
                "average_speed",
                "traffic_density",
                "road_capacity",
                "previous_traffic",
                "hour",
                "historical_accidents",
            ):
                value = features.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    payload[key] = value

        try:
            async with self._create_client() as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    async def get_accident_hotspots(self, location: str) -> Dict[str, Any]:
        url = settings.hotspots_predict_url
        payload = {
            "location": location,
            "area": location
        }

        try:
            async with self._create_client() as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code == 405:  # If endpoint expects GET
                    resp = await client.get(f"{url}?location={location}", headers=self._get_headers())
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    async def get_latest_traffic_predictions(self, limit: int = 1000) -> Dict[str, Any]:
        url = settings.traffic_latest_url
        try:
            async with self._create_client() as client:
                resp = await client.get(url, params={"limit": limit}, headers=self._get_headers())
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    async def get_latest_accident_hotspots(self, limit: int = 200) -> Dict[str, Any]:
        url = settings.hotspots_list_url
        try:
            async with self._create_client() as client:
                resp = await client.get(url, params={"limit": limit}, headers=self._get_headers())
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    async def get_weather(self, location: str) -> Dict[str, Any]:
        url = settings.weather_url
        geo_url = f"{settings.BACKEND_BASE_URL.rstrip('/')}/geo/search"

        try:
            async with self._create_client() as client:
                geo_response = await client.get(
                    geo_url,
                    params={"query": location, "city": "Hyderabad", "limit": 1},
                )
                geo_response.raise_for_status()
                places = geo_response.json()
                if (
                    not isinstance(places, list)
                    or not places
                    or not isinstance(places[0], dict)
                ):
                    return self._handle_error(
                        ValueError(f"No coordinates found for {location!r}."),
                        geo_url,
                    )

                latitude = places[0].get("latitude")
                longitude = places[0].get("longitude")
                if not isinstance(latitude, (int, float)) or not isinstance(
                    longitude, (int, float)
                ):
                    return self._handle_error(
                        ValueError(f"The location search returned no coordinates for {location!r}."),
                        geo_url,
                    )

                resp = await client.get(
                    url,
                    params={"lat": latitude, "lng": longitude},
                )
                return self._parse_response(resp, url)
        except Exception as e:
            return self._handle_error(e, url)

    # -------------------------------------------------------------
    # Response Parsing & Error Handling (Strictly Direct)
    # -------------------------------------------------------------
    def _parse_response(self, resp: httpx.Response, url: str) -> Dict[str, Any]:
        try:
            data = resp.json()
            if isinstance(data, dict):
                return {
                    "_status_code": resp.status_code,
                    "_endpoint": url,
                    "_is_success": (resp.status_code >= 200 and resp.status_code < 300),
                    **data
                }
            return {
                "_status_code": resp.status_code,
                "_endpoint": url,
                "_is_success": (resp.status_code >= 200 and resp.status_code < 300),
                "data": data
            }
        except Exception:
            return {
                "_status_code": resp.status_code,
                "_endpoint": url,
                "_is_success": (resp.status_code >= 200 and resp.status_code < 300),
                "raw_text": resp.text
            }

    def _handle_error(self, e: Exception, url: str) -> Dict[str, Any]:
        return {
            "_is_success": False,
            "_endpoint": url,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

prediction_client = PredictionServiceClient()
