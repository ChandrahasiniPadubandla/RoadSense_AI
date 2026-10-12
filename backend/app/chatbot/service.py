
from typing import List
from langchain_core.messages import HumanMessage, AIMessage

from app.chatbot.agent import get_agent_executor
from app.chatbot.config import MAX_HISTORY_TURNS, MAX_MESSAGE_LENGTH, is_configured
from app.schemas.chatbot import ChatMessage


class ChatbotError(Exception):
    """Raised for any chatbot failure the router should turn into a clean
    HTTP error — message is always safe to show to the end user."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _history_to_messages(history: List[ChatMessage]):
    messages = []
    for item in history[-MAX_HISTORY_TURNS:]:
        if not item.content or not item.content.strip():
            continue
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
    return messages


def answer(message: str, history: List[ChatMessage]) -> str:
    message = (message or "").strip()
    if not message:
        raise ChatbotError(400, "Message cannot be empty. Please type a question about Metrivon traffic, routes, or accident risk.")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ChatbotError(400, f"Message is too long (max {MAX_MESSAGE_LENGTH} characters). Please shorten your question.")

    if not is_configured():
        raise ChatbotError(503, "AI service is temporarily unavailable. Please try again.")

    try:
        executor = get_agent_executor()
    except RuntimeError:
        raise ChatbotError(503, "AI service is temporarily unavailable. Please try again.")

    chat_history = _history_to_messages(history)

    try:
        result = executor.invoke({"input": message, "chat_history": chat_history})
    except Exception as exc:
        # Any Groq/network/agent-loop failure lands here — never leak the
        # raw exception (which may contain request internals) to the client.
        print(f"[chatbot] agent invocation failed: {exc.__class__.__name__}: {exc}")
        raise ChatbotError(502, "AI service is temporarily unavailable. Please try again.")

    output = (result.get("output") or "").strip()
    if not output:
        raise ChatbotError(502, "AI service is temporarily unavailable. Please try again.")
    return output
