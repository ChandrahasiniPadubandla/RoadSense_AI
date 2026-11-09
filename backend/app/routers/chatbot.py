import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Ensure smart_traffic_chatbot is in sys.path
SMART_CHATBOT_DIR = Path(__file__).resolve().parents[3] / "smart_traffic_chatbot"
if str(SMART_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(SMART_CHATBOT_DIR))

from chatbot import chatbot
from src.config import settings

from app.database.connection import get_db
from app.database.models import ChatHistory
from app.security import get_optional_current_user
from app.schemas.chatbot import ChatRequest, ChatResponse

router = APIRouter(
    prefix="/chatbot",
    tags=["AI Chatbot"]
)


class ChatInput(BaseModel):
    message: str = Field(..., example="Predict traffic congestion between Uppal and Madhapur")
    model_name: Optional[str] = Field(None, example="Linear SVC (Calibrated)")
    conversation_id: Optional[str] = Field(None, example="user-session-123")
    history: Optional[List[Dict[str, Any]]] = None


class WeatherEndpointInput(BaseModel):
    weather_endpoint: str = Field(..., example="/weather/current")


def _save_message_to_db(
    db: Session,
    user_id: Optional[UUID],
    conversation_id: Optional[str],
    role: str,
    content: str,
    intent: Optional[str] = None,
    model_triggered: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[ChatHistory]:
    """Helper to safely persist messages to Supabase without failing requests if table is missing."""
    try:
        record = ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            model_triggered=model_triggered,
            metadata_json=metadata or {},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception as db_err:
        db.rollback()
        # Non-fatal log so chatbot still works even before user runs the SQL script
        print(f"[Chatbot DB] Persistence notice: {db_err}")
        return None


@router.get("/health", summary="Chatbot service health check")
def health():
    return {"status": "ok", "configured": True, "engine": "smart_traffic_chatbot"}


@router.post("/message", response_model=ChatResponse, summary="Send message to Chatbot (ChatWidget endpoint)")
async def chatbot_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_current_user),
):
    """
    Main endpoint used by the frontend ChatWidget component.
    Processes the user's message with intent classification, NER location extraction,
    returns a structured response, and stores history in Supabase.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 1. Save user query in DB
    _save_message_to_db(
        db=db,
        user_id=user_id,
        conversation_id=request.conversation_id,
        role="user",
        content=request.message.strip(),
    )

    try:
        result = await chatbot.chat_async(
            message=request.message.strip(),
            model_name=request.model_name,
            conversation_id=request.conversation_id,
        )
        reply = result.get("response_text", "")

        # 2. Save assistant response in DB
        _save_message_to_db(
            db=db,
            user_id=user_id,
            conversation_id=request.conversation_id,
            role="assistant",
            content=reply,
            intent=result.get("intent"),
            model_triggered=result.get("model_triggered"),
            metadata={
                "confidence": result.get("confidence"),
                "start_location": result.get("start_location"),
                "end_location": result.get("end_location"),
                "map_url": result.get("map_url"),
                "api_response": result.get("api_response"),
            },
        )

        return {
            "reply": reply,
            "mode": "smart_traffic_chatbot",
            **result,
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/chat", summary="Chat with the Traffic & Accident AI Assistant (smart_traffic_chatbot endpoint)")
async def chat_api(
    req: ChatInput,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_current_user),
):
    """
    Classifies user intent, extracts locations via spaCy NER/patterns,
    dispatches query to the respective backend prediction service, and stores chat history.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Save user message
    _save_message_to_db(
        db=db,
        user_id=user_id,
        conversation_id=req.conversation_id,
        role="user",
        content=req.message.strip(),
    )

    result = await chatbot.chat_async(
        message=req.message.strip(),
        model_name=req.model_name,
        conversation_id=req.conversation_id,
    )
    reply = result.get("response_text", "")
    result["reply"] = reply
    result["mode"] = "smart_traffic_chatbot"

    # Save assistant message
    _save_message_to_db(
        db=db,
        user_id=user_id,
        conversation_id=req.conversation_id,
        role="assistant",
        content=reply,
        intent=result.get("intent"),
        model_triggered=result.get("model_triggered"),
        metadata={
            "confidence": result.get("confidence"),
            "start_location": result.get("start_location"),
            "end_location": result.get("end_location"),
            "map_url": result.get("map_url"),
            "api_response": result.get("api_response"),
        },
    )

    return result


@router.get("/history", summary="Fetch conversation history for current user or session")
def get_chat_history(
    conversation_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_current_user),
):
    """
    Returns saved conversation messages for the authenticated user or guest conversation ID.
    """
    try:
        query = db.query(ChatHistory)
        if user_id:
            query = query.filter(ChatHistory.user_id == user_id)
        elif conversation_id:
            query = query.filter(ChatHistory.conversation_id == conversation_id)
        else:
            return {"messages": []}

        records = query.order_by(ChatHistory.created_at.asc()).limit(limit).all()
        return {
            "messages": [
                {
                    "message_id": str(r.message_id),
                    "role": r.role,
                    "content": r.content,
                    "text": r.content,
                    "sender": "Metrivon AI" if r.role == "assistant" else "You",
                    "intent": r.intent,
                    "model_triggered": r.model_triggered,
                    "metadata": r.metadata_json or {},
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        }
    except Exception as err:
        db.rollback()
        # Return empty list if table not yet created
        return {"messages": [], "warning": str(err)}


@router.delete("/history", summary="Clear conversation history for current user or session")
def clear_chat_history(
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_optional_current_user),
):
    """
    Deletes conversation messages for the authenticated user or session ID.
    """
    try:
        query = db.query(ChatHistory)
        if user_id:
            if conversation_id:
                query = query.filter(ChatHistory.user_id == user_id, ChatHistory.conversation_id == conversation_id)
            else:
                query = query.filter(ChatHistory.user_id == user_id)
        elif conversation_id:
            query = query.filter(ChatHistory.conversation_id == conversation_id)
        else:
            return {"status": "noop", "deleted_count": 0}

        count = query.delete(synchronize_session=False)
        db.commit()
        return {"status": "success", "deleted_count": count}
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))


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
