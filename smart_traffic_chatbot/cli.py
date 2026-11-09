import sys
import asyncio
from uuid import uuid4
from src.chatbot_engine import chatbot_engine
from src.config import settings

async def run_cli():
    # Set UTF-8 encoding for standard output on Windows
    sys.stdout.reconfigure(encoding='utf-8')
    conversation_id = str(uuid4())

    print("\n" + "=" * 75)
    print("🚦 ROADPULSE AI - TERMINAL TRAFFIC & ACCIDENT CHATBOT")
    print("=" * 75)
    print(f"Classifier Model     : {chatbot_engine.active_model_name}")
    print("Location Extractor   : spaCy NER + Pattern Fallback (Start & End Locations)")
    print(f"Backend API Base URL : {settings.BACKEND_BASE_URL}")
    print("\nAvailable Endpoints & Models:")
    print("  1. Traffic Prediction   : POST /predictions/traffic/route")
    print("  2. Accident Risk        : POST /predictions/accidents/route")
    print("  3. Anomaly Detection    : POST /anomalies/predict (Isolation Forest)")
    print("  4. Accident Hotspots    : POST /hotspots/predict")
    print("  5. Weather API          : GET  /weather/live (coordinates from /geo/search)")
    print("\nType any query (e.g. 'Predict traffic from Uppal to Madhapur') or 'exit' to quit.\n")
    print("-" * 75 + "\n")

    while True:
        try:
            user_input = input("User >> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Exiting RoadPulse AI. Drive safely!")
                break

            # Process Chat Query
            response = await chatbot_engine.process_message(
                user_input,
                conversation_id=conversation_id,
            )

            # Display formatted output with Model Triggered, Start/End Location, and Raw API Response
            print("\n" + response["response_text"] + "\n")

        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_cli())
