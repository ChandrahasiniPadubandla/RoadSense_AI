import asyncio
from typing import Dict, Any, Optional, List
from src.config import settings
from src.chatbot_engine import chatbot_engine
from src.ner_extractor import location_extractor

class TrafficChatbot:
    """
    Standalone, easily-embeddable Traffic & Accident Chatbot component.
    
    Can be imported directly into your existing application:
    --------------------------------------------------------
    from chatbot import TrafficChatbot

    bot = TrafficChatbot(backend_base_url=http://127.0.0.1:8000 ")
    
    # 1. Asynchronous query (for FastAPI / AsyncIO)
    response = await bot.chat_async("Predict traffic from Uppal to Madhapur")
    
    # 2. Synchronous query
    response = bot.chat("Estimate accident risk near Banjara Hills")
    """

    def __init__(
        self,
        backend_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        mock_fallback: bool = True
    ):
        if backend_base_url:
            settings.BACKEND_BASE_URL = backend_base_url.rstrip("/")
        if model_name:
            chatbot_engine.set_active_model(model_name)
        settings.MOCK_FALLBACK_ENABLED = mock_fallback

    def set_backend_url(self, backend_url: str):
        """Update backend base URL (e.g. http://10.30.0.231:8000)."""
        settings.BACKEND_BASE_URL = backend_url.rstrip("/")

    def set_weather_endpoint(self, weather_route: str):
        """Set or update the custom weather endpoint once available."""
        settings.WEATHER_ENDPOINT = weather_route if weather_route.startswith("/") else f"/{weather_route}"

    def set_active_model(self, model_name: str) -> bool:
        """Switch active intent classification algorithm."""
        return chatbot_engine.set_active_model(model_name)

    def list_models(self) -> List[Dict[str, Any]]:
        """List active model details."""
        return chatbot_engine.list_available_models()

    async def chat_async(
        self,
        message: str,
        model_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process user query asynchronously.
        
        Returns:
            dict containing:
            - query (str)
            - intent (str): traffic_prediction | accident_prediction | anomaly_query | hotspot_query | weather_prediction
            - confidence (float): 0.0 to 1.0
            - model_triggered (str): which backend model/endpoint was called
            - start_location (str): origin location
            - end_location (str): destination location
            - api_response (dict): exact JSON / dict returned by the API
            - response_text (str): formatted human-friendly markdown response
        """
        return await chatbot_engine.process_message(
            user_message=message,
            model_name=model_name,
            conversation_id=conversation_id,
        )

    def chat(
        self,
        message: str,
        model_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for chat_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass
            return loop.run_until_complete(
                self.chat_async(message, model_name, conversation_id)
            )
        else:
            return asyncio.run(self.chat_async(message, model_name, conversation_id))

    def extract_locations(self, text: str) -> Dict[str, Any]:
        """Utility method to run spaCy NER + Pattern fallback location extraction directly."""
        return location_extractor.extract(text)

# Default singleton instance
chatbot = TrafficChatbot()

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    sample = "Predict traffic congestion between Miyapur and Hitech City"
    res = chatbot.chat(sample)
    print("\n" + res["response_text"])
