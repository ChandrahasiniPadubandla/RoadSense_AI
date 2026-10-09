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
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest tests/test_suggestion_reproducibility.py -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The startup log should report `READY`. Confirm the database target, required
shared data, and the shared geocoder cache at:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/public/readiness | ConvertTo-Json -Depth 6
```

It must show `status: READY`, `database.connected: true`,
`database.schema_ready: true`, non-zero `roads`, `traffic_records`, and
`accidents`, and both migration checks true. If the cache table is missing or
either migration marker is absent, ask the database administrator to run both
files in `database/migrations/` against the shared DB.
If the required record counts are zero, ask the project data steward to load
the approved shared data; do not seed from local CSV files.

In a second terminal:

```powershell
Copy-Item frontend/.env.example frontend/.env.local
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. `VITE_API_BASE_URL` selects only the backend
origin; database credentials and provider configuration stay in the backend.

All geocode suggestions are clipped to the fixed Hyderabad boundary. The
request's `city` parameter remains accepted for compatibility but cannot widen
the boundary or change the provider bias. Provider results are stored in the
shared database so all backend instances use the same cached response for a
query. The exact configuration and migration instructions are in
[`../database/README.md`](../database/README.md).
