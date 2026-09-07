import os
import requests
from typing import Optional, Any


class RoadSenseAPIClient:
    """
    Client for interacting with RoadSense AI FastAPI Backend.
    Enforces API-first pattern: fetches data and stores predictions exclusively
    through REST APIs without querying the database directly.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("ROADSENSE_API_TOKEN")

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def set_token(self, token: str):
        self.token = token

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.request(method, url, headers=self._get_headers(), **kwargs)
                if resp.status_code < 500:
                    resp.raise_for_status()
                    return resp
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                resp.raise_for_status()
                return resp
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                raise e

    # =========================================================
    # GET APIS (Data Ingestion)
    # =========================================================

    def get_roads(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/roads"
        resp = self._request_with_retry("GET", url)
        return resp.json()

    def get_zones(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/zones"
        resp = self._request_with_retry("GET", url)
        return resp.json()

    def get_traffic_records(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/traffic"
        resp = self._request_with_retry("GET", url)
        return resp.json()

    def get_weather_records(self, limit: int = 2000) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/weather?limit={limit}"
        resp = self._request_with_retry("GET", url)
        return resp.json()

    def get_accidents(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/accidents"
        resp = self._request_with_retry("GET", url)
        return resp.json()

    # =========================================================
    # POST APIS (Prediction Storage)
    # =========================================================

    def post_traffic_prediction(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/predictions/traffic"
        resp = self._request_with_retry("POST", url, json=payload)
        return resp.json()

    def post_accident_prediction(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/predictions/accidents"
        resp = self._request_with_retry("POST", url, json=payload)
        return resp.json()

    def trigger_anomaly_scan(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/anomalies/detect"
        resp = self._request_with_retry("POST", url)
        return resp.json()

