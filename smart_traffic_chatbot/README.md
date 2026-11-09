# RoadPulse AI: Smart Traffic & Accident Prediction Chatbot

An intelligent, terminal-ready conversational AI component engineered for **Traffic Congestion Prediction**, **Accident Risk Forecasting**, **Traffic Flow Anomaly Detection**, **Historical Blackspot Queries**, and **Live Weather Advisory**.

The chatbot features:
1. **Calibrated Linear SVC Intent Classifier**: Top-ranked model trained on `data/fresh_chatbot_dataset.csv` with 92.9% 5-fold cross-validation accuracy.
2. **Hybrid NER Location Extractor**: Domain-adapted `spaCy` NER (`en_core_web_sm`) + Regex corridor detection (`Origin -> Destination`) + Telangana transport gazetteer.
3. **Backend Location Search**: Places not in the built-in Hyderabad gazetteer are resolved through the backend `/geo/search` service before route predictions.
4. **Direct FastAPI Microservice Integration**: Direct HTTP calls to your live backend without mock/simulated fallbacks. Displays the relevant API fields for traffic, accident-risk, and distance requests; the complete response remains available as `api_response`.

---

## 🚀 Terminal Usage

Run the chatbot interactively:
```bash
python cli.py
```

If a message contains a route but does not say what information is needed, the
chatbot asks whether you want traffic, accident risk, distance, anomalies,
hotspots, or weather before calling a prediction endpoint. Greetings such as
`hello`, `hey`, and `good morning` receive a greeting and a list of supported
topics. It also asks for missing details in either order: a route can be entered
before the service, or the service can be selected before the route. CLI
conversations retain that pending context. For API conversations, send the same
`conversation_id` with each message to retain the selected service, route, or
partially entered locations.

Route responses are limited to the requested result:

- Traffic: start/end locations, distance, congestion level, and estimated time.
- Traffic requests with a relative departure delay (for example, `start in 60 minutes`) include an ISO 8601 `target_time` in the route prediction API payload, using the Hyderabad time-zone offset. Requests without a departure time keep the existing payload.
- Accident risk: start/end locations, distance, risk percentage and level, and historical accident count.
- Combined traffic and accident-risk requests call both route prediction endpoints and report both results.
- Citywide questions about traffic or accident areas query the backend's latest traffic predictions and database-backed accident hotspots. They filter by the level in the question (`HIGH`, `MEDIUM`, `LOW`, or `SEVERE` / `sever`), default to `HIGH` when none is specified, and return up to five areas per requested category.
- Accident area severity uses the backend-provided risk level; historical accident counts are shown as context and do not determine the risk level.
- Distance: distance only.
- Route responses also include a `map_url` linking to the frontend live map with `start_location` and `end_location` query parameters. Configure `LIVE_MAP_URL` if the frontend is not hosted at `http://localhost:5173/live-map`. The authenticated frontend opens the directions view and draws the route from those parameters.

---

## 🧩 Integration into Your Existing Application

### Option A: Import Direct Python Class
```python
from chatbot import TrafficChatbot

bot = TrafficChatbot(backend_base_url="http://10.30.0.231:8000")

# Synchronous
result = bot.chat("Predict traffic from Uppal to Madhapur")

# Asynchronous multi-turn conversation
result = await bot.chat_async(
    "Kukatpally to Kompally",
    conversation_id="my-session",
)
result = await bot.chat_async("traffic", conversation_id="my-session")

# Or select a service first and provide the route after the prompt:
result = await bot.chat_async("accident risk", conversation_id="another-session")
result = await bot.chat_async(
    "Uppal to Nagole",
    conversation_id="another-session",
)

# Access extracted data directly:
print(result["model_triggered"])  # Model & endpoint called
print(result["start_location"])   # Origin
print(result["end_location"])     # Destination
print(result["api_response"])     # Exact raw JSON from backend
print(result["response_text"])    # Formatted terminal display
```

### Option B: Mount as a FastAPI Sub-Router
```python
from fastapi import FastAPI
from chatbot_router import router as chatbot_router

app = FastAPI()
app.include_router(chatbot_router, prefix="/chatbot", tags=["AI Chatbot"])
```

---

## 🔗 Connected Backend Endpoints

| User Intent | Backend Endpoint | Method |
| :--- | :--- | :---: |
| **Traffic Congestion** | `/predictions/traffic/route` | `POST` |
| **Accident Risk** | `/predictions/accidents/route` | `POST` |
| **Traffic Anomalies** | `/anomalies/predict` | `POST` |
| **Accident Hotspots** | `/hotspots/predict` | `POST` |
| **Latest Traffic Areas** | `/predictions/traffic/latest` | `GET` |
| **Database Accident Areas** | `/hotspots` | `GET` |
| **Weather Conditions** | `/weather/live` | `GET` with `lat` and `lng` from `/geo/search` |

---

## 📁 Repository Structure

```
smart_trafffic_chatbot/
├── data/
│   └── fresh_chatbot_dataset.csv     # Training dataset
├── models/
│   ├── best_model.pkl                 # Linear SVC production model
│   ├── tfidf_vectorizer.pkl           # Fitted sublinear (1,3)-gram TF-IDF
│   └── label_encoder.pkl              # Target encoder
├── src/
│   ├── config.py                      # Endpoint & timeout settings
│   ├── ner_extractor.py               # spaCy NER + Pattern fallback
│   ├── model_trainer.py               # Model training pipeline
│   ├── prediction_client.py           # Direct backend HTTP client (no fallbacks)
│   └── chatbot_engine.py              # Core intelligence orchestrator
├── chatbot.py                         # Standalone importable TrafficChatbot class
├── chatbot_router.py                  # FastAPI APIRouter for existing application
├── cli.py                             # Interactive terminal CLI
└── requirements.txt                   # Application dependencies
```
