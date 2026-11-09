import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "Smart Traffic & Accident AI Chatbot"
    DATASET_PATH: str = str(DATA_DIR / "fresh_chatbot_dataset.csv")
    MODELS_DIR: str = str(MODELS_DIR)
    
    # Active intent classifier
    DEFAULT_MODEL: str = "Linear SVC (Calibrated)"
    CONFIDENCE_THRESHOLD: float = 0.40

    # User Backend API Base URL
    BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    LIVE_MAP_URL: str = os.getenv("LIVE_MAP_URL", "/live-map")

    # Backend Endpoints
    # 1. Traffic Prediction for User Start & End Locations
    TRAFFIC_ROUTE_ENDPOINT: str = "/predictions/traffic/route"
    
    # 2. Accident Risk Prediction for User Start & End Locations
    ACCIDENT_ROUTE_ENDPOINT: str = "/predictions/accidents/route"
    
    # 3. Traffic Anomalies using trained Isolation Forest ML model
    ANOMALIES_PREDICT_ENDPOINT: str = "/anomalies/predict"
    
    # 4. Accident Hotspots Prediction
    HOTSPOTS_PREDICT_ENDPOINT: str = "/hotspots/predict"

    # Read-only, database-backed citywide area lookups
    TRAFFIC_LATEST_ENDPOINT: str = "/predictions/traffic/latest"
    HOTSPOTS_LIST_ENDPOINT: str = "/hotspots"
    
    # 5. Live weather API route; weather lookup geocodes place names first.
    WEATHER_ENDPOINT: str = "/weather/live"

    # Weather API key or fallback credentials if third-party provider is used
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")

    # Seamless fallback to intelligent simulated ML predictions when backend is offline
    MOCK_FALLBACK_ENABLED: bool = True
    HTTP_TIMEOUT_SECONDS: float = 30.0

    @property
    def traffic_route_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.TRAFFIC_ROUTE_ENDPOINT}"

    @property
    def accident_route_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.ACCIDENT_ROUTE_ENDPOINT}"

    @property
    def anomalies_predict_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.ANOMALIES_PREDICT_ENDPOINT}"

    @property
    def hotspots_predict_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.HOTSPOTS_PREDICT_ENDPOINT}"

    @property
    def traffic_latest_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.TRAFFIC_LATEST_ENDPOINT}"

    @property
    def hotspots_list_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.HOTSPOTS_LIST_ENDPOINT}"

    @property
    def weather_url(self) -> str:
        return f"{self.BACKEND_BASE_URL.rstrip('/')}{self.WEATHER_ENDPOINT}"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
