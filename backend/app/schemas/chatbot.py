from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[ChatMessage] = []
    conversation_id: Optional[str] = None
    model_name: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    mode: str = "smart_traffic_chatbot"
    query: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    model_triggered: Optional[str] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    api_response: Optional[Dict[str, Any]] = None
    response_text: Optional[str] = None
    map_url: Optional[str] = None
