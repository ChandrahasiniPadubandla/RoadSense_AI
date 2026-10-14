# Metrivon AI Backend

This backend exposes the real Metrivon AI APIs and integrates the trained accident-risk model with the existing PostgreSQL database.

## Reproducible team setup

All teammates must set `DATABASE_URL` to the same project-owned PostgreSQL
database. The owner/data steward supplies that URL securely and provisions the
shared roads, traffic observations, accidents, zones, and hotspot records; none
of those private operational records are committed here. Setup and migration
commands are in [`../database/README.md`](../database/README.md).

Place suggestions are requested by the frontend from `GET /api/geo/search` and
resolved by the backend against Photon plus monitored road records from that
database. Results are restricted to the fixed Hyderabad boundary and Photon
candidates are cached in the shared database, not in a per-process cache.
Photon is free and needs no API key. The readiness check is
`GET /api/public/readiness`; it reports a safe host/database identifier,
required shared-data counts, geocoder settings, and cache migration state.

Traffic observations and accident counts come from the shared
`traffic_records` and `accidents` tables. Hotspot generation and route-risk
context use database records; checkout-local `accident_hotspots.csv` values
are not used as operational data. Prediction model artifacts are versioned in
`predict_accident_risk/` and `traffic_congestion/`, with repository-relative
paths. No API key is required for geocoding or traffic inputs.

## Real database architecture used for prediction

The accident-risk prediction pipeline reads road, traffic, and historical
accident inputs from the configured project database:

- roads: road metadata and coordinates
  - road_id
  - road_name
  - road_type
  - road_capacity
  - road_condition
  - start_location
  - end_location
- traffic_records: latest traffic measurement for a road
  - road_id
  - timestamp
  - vehicle_count
  - average_speed
  - traffic_density
  - congestion_level
  - rainfall
  - temperature
  - visibility
  - is_holiday
- accidents: historical accident count by road
  - road_id
  - accident_datetime
- weather is fetched from the existing live weather service when needed and validated against the road coordinates

Weather is an external enrichment. Traffic observations and accident history
come from the shared database; hotspot outputs are persisted there.

## Model files required

The service expects these versioned files in the repository's
`predict_accident_risk/` directory (not `backend/app/ml/models/`):

- predict_accident_risk/accident_risk_classifier.json
- predict_accident_risk/accident_risk_regressor.json
- predict_accident_risk/accident_preprocessor.pkl
- predict_accident_risk/accident_label_encoder.pkl

These are loaded once and reused for all prediction requests.

## Voice location NER model

The voice route extractor loads a trained spaCy NER model (labels
`START_LOCATION` / `END_LOCATION`). The model is committed to this repository so
every clone uses the identical artifact — there is nothing to download and no
credentials are required.

- Committed location: `voice.zip/location_ner_model`
- Legacy fallback checked as well: `voice_extractor/location_ner_model`
- spaCy version recorded by the model: `>=3.8.16,<3.9.0`
- `ner/model` SHA-256: `ee1db62316747d3965a434daab93b09d4b7e2c20d776142e7260ebcf2490c751`

The resolver picks the first of those directories that contains a `meta.json`.
You can override it for advanced setups with the `VOICE_NER_MODEL_PATH`
environment variable. Do not commit a different model without updating
`backend/tests/test_voice_location_resolution.py` and this section.

Verify the model is present and loaded:

```bash
python -c "from app.services.voice_service import get_nlp_model; print('loaded:', get_nlp_model() is not None)"
```

`GET /api/voice/status` returns `model_loaded` plus the resolved `model_path`.
If `model_loaded` is `false`, the backend is running from a partial checkout
without the committed `voice.zip/location_ner_model` directory.

## Dependencies

The backend requires these packages from backend/requirements.txt:

- FastAPI
- SQLAlchemy
- Pydantic
- scikit-learn
- joblib
- pandas
- numpy
- xgboost
- spacy (required to load the committed voice location NER model)
- uvicorn

## Environment configuration

`backend/.env` is git-ignored and is not part of the repository. Copy the
template and fill in the values you have access to:

```bash
copy backend\.env.example backend\.env   # Windows
```

Required values: the shared `DATABASE_URL` (get it from the project owner) and
`JWT_SECRET_KEY`. Keep database credentials, chatbot keys, SMTP credentials,
and all other private values out of frontend environment files and Git.
Photon geocoding requires no API key.

## Start backend

From the backend directory:

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Binding to `0.0.0.0` allows teammates on the same trusted LAN to reach this
backend. Share this computer's LAN IP with them; they should set
`VITE_API_BASE_URL=http://<backend-host-ip>:8000` in their local
`frontend/.env` and restart Vite. Do not use `127.0.0.1` in their frontend
configuration, since that points to each teammate's own computer.

On Windows, allow inbound TCP port 8000 only from the trusted LAN subnet in an
elevated PowerShell. Replace the example subnet with the subnet used by the
backend host:

```powershell
New-NetFirewallRule -DisplayName "RoadSense Backend LAN 8000" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 `
  -RemoteAddress "192.168.88.0/24" -Profile Public
```

Only share the backend on a network you trust. The computer running this
backend must remain on and connected for teammates to use it.

Confirm the intended shared database and required records before using
suggestions or predictions:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/public/readiness | ConvertTo-Json -Depth 6
```

Expected: `status` is `READY`, `database.connected` and `database.schema_ready`
are true, the target matches the team's shared database, roads/traffic/accident
counts are non-zero, and both migration checks are true. The database owner
applies both SQL files under `database/migrations/`
to existing databases. Migration 002 corrects previously stored hotspot values
that may have included checkout-local CSV data.
Run the focused provider and boundary checks with:

```bash
python -m pytest tests/test_suggestion_reproducibility.py -q
```

## Swagger docs

Open:

```text
http://127.0.0.1:8000/docs
```

## Road search endpoint

### Method

GET /api/roads?search=<road_name>

### Example

```text
GET /api/roads?search=Abids
```

### Example response

```json
[
  {
    "road_id": "1a6c5d83-9b04-48e7-f427-d0ae915b6172",
    "road_name": "Abids Main Road"
  }
]
```

## Accident-risk prediction endpoint

### Method

POST /api/accident-predictions/predict

### Request format

```json
{
  "road_id": "1a6c5d83-9b04-48e7-f427-d0ae915b6172"
}
```

This route looks up the real road, derives the necessary ML features from the existing database, and then runs the trained model.

### Response format

```json
{
  "success": true,
  "road_id": "1a6c5d83-9b04-48e7-f427-d0ae915b6172",
  "road_name": "Abids Main Road",
  "accident_risk": 31.56,
  "accident_risk_level": "LOW",
  "model_status": "loaded"
}
```

## Feature derivation rules

The backend does not accept manual ML features from the frontend. It derives them internally from actual database records:

- start_location, end_location, start_latitude, start_longitude, end_latitude, end_longitude from roads.start_location and roads.end_location
- road_type from roads.road_type
- road_capacity from roads.road_capacity
- road_condition from roads.road_condition
- vehicle_count, average_speed, traffic_density, congestion_level from traffic_records for the selected road
- previous_traffic from the previous traffic record for that road
- rainfall, temperature, visibility, weather from the live weather service for the road coordinates
- historical_accidents from the count of accidents tied to the selected road
- hour, day_of_week, holiday from the prediction timestamp and the latest traffic timestamp / calendar data

## Notes

- The frontend sends only road_id; the backend handles all feature assembly.
- If any required dictionary feature is missing from the real database, the API responds with a 422 error instead of fabricating a value.
- The model is loaded once and reused for inference.
- No database records are created or modified during production prediction.
