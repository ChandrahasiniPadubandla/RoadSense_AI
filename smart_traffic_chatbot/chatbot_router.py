from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from chatbot import chatbot
from src.config import settings

router = APIRouter()

class ChatInput(BaseModel):
    message: str = Field(..., example="Predict traffic congestion between Uppal and Madhapur")
    model_name: Optional[str] = Field(None, example="Linear SVC (Calibrated)")
    conversation_id: Optional[str] = Field(None, example="user-session-123")

class WeatherEndpointInput(BaseModel):
    weather_endpoint: str = Field(..., example="/weather/current")

@router.post("/chat", summary="Chat with the Traffic & Accident AI Assistant")
async def chat_api(req: ChatInput):
    """
    Classifies user intent, extracts locations via spaCy NER/patterns,
    dispatches query to the respective backend model endpoint:
    - POST /predictions/traffic/route
    - POST /predictions/accidents/route
    - POST /anomalies/predict (Isolation Forest)
    - POST /hotspots/predict
    - Weather Endpoint

    The response prompts for missing services or locations. Set conversation_id
    on each request to retain pending context across turns.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return await chatbot.chat_async(
        message=req.message.strip(),
        model_name=req.model_name,
        conversation_id=req.conversation_id,
    )

@router.get("/models", summary="List trained intent classification models")
def list_models_api():
    return {
        "active_model": settings.DEFAULT_MODEL,
        "models": chatbot.list_models()
    }

@router.post("/models/select", summary="Switch active classification model")
def select_model_api(model_name: str):
    success = chatbot.set_active_model(model_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not found.")
    return {"status": "success", "active_model": model_name}

@router.post("/config/weather", summary="Configure the weather endpoint route")
def set_weather_route_api(req: WeatherEndpointInput):
    chatbot.set_weather_endpoint(req.weather_endpoint)
    return {
        "status": "success",
        "weather_url": settings.weather_url,
        "message": f"Weather route updated to '{req.weather_endpoint}'"
    }

@router.get("/extract-locations", summary="Direct NER & Pattern Location Extractor")
def extract_locations_api(text: str):
    return chatbot.extract_locations(text)
