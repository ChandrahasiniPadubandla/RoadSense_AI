# Full setup — database → ML → backend → chatbot → frontend

Everything below has been written against your real `schema.sql` (UUID
primary keys, PostGIS `GEOGRAPHY(POINT)` columns), `seed_roles.sql`, and the
`traffic_accident_master_7000.csv` dataset. Follow the sections in order —
each one depends on the previous.

```
smart-traffic-dashboard/
  database/              schema.sql, seed_roles.sql, seed_roads_zones.sql, seed_users.py
  ml-training/            train_traffic_model.py, train_accident_model.py, data/, models/
  backend/                FastAPI REST API + chatbot router (app/routers/chatbot.py)
  chatbot-backend-reference/   standalone chatbot service (optional — see note below)
  src/, package.json...   the React frontend
```

**Note on the chatbot**: it now lives inside `backend/app/routers/chatbot.py`
so the frontend only talks to one base URL. `chatbot-backend-reference/` is
kept as a reference/fallback if you ever want it as a separate microservice
instead — you don't need to run both.

---

## 1. Database

Requires PostgreSQL with the PostGIS extension.

```bash
createdb smart_traffic
psql smart_traffic -c "CREATE EXTENSION IF NOT EXISTS postgis;"

cd database
psql smart_traffic -f schema.sql
psql smart_traffic -f seed_roles.sql
psql smart_traffic -f seed_roads_zones.sql

pip install psycopg2-binary passlib[bcrypt] python-dotenv --break-system-packages
echo "DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/smart_traffic" > .env
python seed_users.py
```

This gives you: 4 roles, the 12 real roads from the dataset (with zones),
and 4 demo login accounts (`admin@traffic.gov` / `admin123`, etc. — see
`database/seed_users.py` for the full list).

**You still need traffic_records rows** for predictions/dashboard stats to
show real numbers (the ML models predict FROM the latest traffic_records
row per road). Two options:
- Quick: load a slice of `ml-training/data/traffic_accident_master_7000.csv`
  into `traffic_records` yourself (map columns to the table — see
  `ml-training/train_traffic_model.py`'s feature list for which ones matter), or
- Proper: build a small ingestion script/IoT feed later per DPR's
  "extensible architecture for IoT/camera integration" goal — out of scope
  for this pass, flag if you want it built.

---

## 2. Train the two ML models (fully separate, as requested)

```bash
cd ml-training
pip install -r requirements.txt --break-system-packages
python train_traffic_model.py     # -> models/traffic_model.joblib
python train_accident_model.py    # -> models/accident_risk_regressor.joblib
                                   # -> models/accident_risk_classifier.joblib
```

Both were run against your actual dataset while building this:
- **Traffic model**: 72.9% accuracy classifying LOW/MEDIUM/HIGH/SEVERE congestion
- **Accident risk model**: MAE 5.46 / R² 0.75 on risk %, 86% accuracy on risk level

These numbers are a starting point, not a ceiling — see "Improving the
models" at the bottom.

---

## 3. Backend (REST API + chatbot)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `DATABASE_URL` — same one used in step 1
- `JWT_SECRET_KEY` — any long random string
- `OPENAI_API_KEY` — for the chatbot router
- `TRAFFIC_MODEL_PATH` / `ACCIDENT_RISK_*_PATH` — point at the `.joblib`
  files from step 2 (defaults already match the folder layout above)

```bash
uvicorn app.main:app --reload --port 8000
```

Test it: open `http://localhost:8000/docs` — FastAPI's auto-generated,
interactive API explorer. Try `POST /api/auth/login` with
`admin@traffic.gov` / `admin123` first; copy the `accessToken` and use the
"Authorize" button for the rest.

---

## 4. Frontend

```bash
cd .. # back to smart-traffic-dashboard root
npm install
cp .env.example .env
```

Edit `.env`:
```
VITE_API_BASE_URL=http://localhost:8000/api
VITE_USE_MOCK_DATA=false
```

```bash
npm run dev
```

Open `http://localhost:5173`, log in with a seeded account.

---

## What to click first, to see the whole system work end to end

1. Log in as `admin@traffic.gov`
2. **Traffic Monitoring** — should show your 12 roads (empty stats until
   traffic_records has data — see step 1's note)
3. Once traffic_records has rows: **Congestion Prediction** and **Accident
   Risk Prediction** — these call the trained models live and write results
   into `traffic_predictions`/`accident_predictions`
4. **Traffic & Risk Overview** — the merged view combining both per road
5. **Accident Management** — record an accident against a real road; if you
   mark it SEVERE/FATAL, it auto-creates an **Emergency Response** entry
6. **Emergency Response** — advance PENDING → EN_ROUTE → ON_SCENE → RESOLVED
7. Chat bubble (bottom-right) — ask "which road has the highest accident risk?"

---

## Improving the models later

- **More/better features**: `historical_accidents` currently comes from a
  live `COUNT(*)` in `accidents.py` — fine for now, but a rolling window
  (e.g. accidents in the last 90 days) would match the DPR's intent more
  precisely.
- **Anomaly detection** currently uses a simple 2x-average rule
  (`traffic.py`'s `get_anomalies`), not a trained model — swap in
  `IsolationForest` or similar if you want it ML-driven per Module 7.
- **Retraining cadence**: as real `traffic_records`/`accidents` accumulate,
  periodically re-run the two training scripts against a fresh export and
  swap the `.joblib` files — no backend code changes needed.
