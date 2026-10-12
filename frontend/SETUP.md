# Team development setup

The backend and frontend use the shared project configuration described in
[`../database/README.md`](../database/README.md). Traffic records and accidents
are read from the project PostgreSQL database. Do not import the training CSVs
as operational records or use a developer-specific database.

## Prerequisites

- Node.js 20 or newer.
- Python 3.12 and the backend requirements.
- The project owner's shared PostgreSQL `DATABASE_URL` and a private JWT
  signing key. The owner/data steward also provisions the shared roads,
  `traffic_records`, and accident data. Photon location search needs no key.

## Start from a clone (PowerShell)

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env`: set `DATABASE_URL` to the same team URL used by every
teammate and set a private `JWT_SECRET_KEY`. Do not commit this file. Generate
a local key with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Install and start the backend:

```powershell
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
