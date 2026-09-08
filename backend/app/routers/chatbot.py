import os
from typing import List, Dict
from fastapi import APIRouter, HTTPException

from app.schemas.chatbot import ChatMessage, ChatRequest, ChatResponse

router = APIRouter(
    prefix="/api/chatbot",
    tags=["AI Chatbot"]
)

SYSTEM_PROMPT = """You are the Smart Traffic AI Assistant for an AI-based smart traffic and accident prediction system.
Answer questions related to traffic congestion, traffic prediction, accident risk, accident hotspots, anomalies,
alerts, emergency response, maps, and the application's modules. Be clear and practical. Do not invent live traffic
or accident data. If the user asks for live/current data that is not provided to you, clearly say that the system
does not currently have a live traffic data feed connected. You can explain how the system would use such data."""


def fallback_answer(message: str) -> str:
    text = message.lower().strip()
    if any(w in text for w in ["hello", "hi", "hey"]):
        return "Hello! I’m the Smart Traffic AI Assistant. I can explain traffic prediction, accident risk, hotspots, anomalies, alerts, emergency response, and the project modules."
    if "live" in text or "real time" in text or "realtime" in text:
        return "The chatbot does not have a live traffic or CCTV feed connected yet. It can explain the architecture and work with live data once a traffic-data API, IoT feed, or camera pipeline is connected."
    if "traffic" in text or "congestion" in text:
        return "Traffic prediction can use vehicle count, average speed, traffic density, road condition, weather, rainfall, visibility, time and historical traffic patterns to estimate congestion levels."
    if "hotspot" in text:
        return "An accident hotspot is a location or zone where historical accidents are concentrated. Hotspots can be calculated from accident records and displayed on a map with risk levels."
    if "accident" in text or "risk" in text:
        return "Accident-risk prediction can use traffic density, speed, weather, rainfall, visibility, road condition, time, historical accidents and vehicle-related features to estimate a risk percentage or risk level."
    if "anomal" in text:
        return "Anomaly detection identifies unusual traffic behaviour, such as an unexpected vehicle-count increase or speed drop compared with normal patterns."
    if "alert" in text:
        return "Alerts can be generated when traffic congestion, accident risk, or an unusual traffic anomaly crosses a configured threshold."
    if "emergency" in text:
        return "The Emergency Response module can assign responders to recorded accidents and track statuses such as pending, assigned, arrived, and resolved."
    if "module" in text:
        return "The main modules are Dashboard, Traffic Monitoring, Accident Management, Predictions, Map, Alerts, Emergency Response, Administration, and the AI Chatbot."
    return "I can help with traffic prediction, accident risk, hotspots, anomalies, alerts, emergency response, maps, and the Smart Traffic application. Ask me a specific question."


def ai_answer(message: str, history: List[ChatMessage]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback_answer(message)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        input_items: List[Dict[str, str]] = []
        for item in history[-10:]:
            if item.role in {"user", "assistant"} and item.content.strip():
                input_items.append({"role": item.role, "content": item.content})
        input_items.append({"role": "user", "content": message})

        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            instructions=SYSTEM_PROMPT,
            input=input_items,
        )
        return response.output_text.strip()
    except ImportError:
        return fallback_answer(message)
    except Exception as exc:
        print(f"OpenAI error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="The AI service could not generate a response. Check your OpenAI API key and model name."
        )


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/message", response_model=ChatResponse)
def chatbot_message(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    reply = ai_answer(request.message, request.history)
    return {
        "reply": reply,
        "mode": "openai" if api_key else "local-fallback"
    }
