"""
Metrivon AI Chatbot endpoint.

    React ChatWidget
        v  POST /api/chatbot/message  { message, history }
    FastAPI (this router)
        v
    app.chatbot.service.answer()
        v
    LangChain AgentExecutor (app.chatbot.agent)
        v
    Groq (openai/gpt-oss-120b)
        v
    Metrivon tools (app.chatbot.tools) -> existing ML/DB services
        v
    natural-language reply, grounded only in real tool results

This REPLACES the previous basic OpenAI-direct-call + keyword-fallback
chatbot. See the project change report for exactly what was removed.
"""
from fastapi import APIRouter, HTTPException

from app.schemas.chatbot import ChatRequest, ChatResponse
from app.chatbot.service import answer, ChatbotError
from app.chatbot.config import is_configured

router = APIRouter(
    prefix="/chatbot",
    tags=["AI Chatbot"]
)


@router.get("/health")
def health():
    return {"status": "ok", "configured": is_configured()}


@router.post("/message", response_model=ChatResponse)
def chatbot_message(request: ChatRequest):
    try:
        reply = answer(request.message, request.history)
    except ChatbotError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message)

    return {"reply": reply, "mode": "groq"}
