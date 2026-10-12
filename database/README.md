# Shared database setup

## Data ownership

The application reads roads, traffic observations, accidents, zones, and
hotspots from PostgreSQL. `schema.sql` and `seed.sql` create the schema and
roles; they do not contain the project traffic or accident records. Those
records are not included in Git. The project owner or data steward must
provision one team PostgreSQL database, import the approved shared records,
and give each teammate the same `DATABASE_URL` through the team's approved
secret-sharing channel. Do not use a developer's private database or load the
model-training CSVs as operational records.

The database service and its credentials are external prerequisites. This
repository does not provision Supabase/PostgreSQL or contain private accident
data. The owner must ensure the shared database contains non-empty `roads`,
`traffic_records`, and `accidents` tables. Hotspots are calculated from those
database records and stored in `accident_hotspots`.

## New shared PostgreSQL database (owner/data steward only)

Create PostgreSQL with PostGIS enabled, then run from the repository root:

```powershell
$env:PGPASSWORD = '<password supplied by your database provider>'
psql 'postgresql://<user>@<host>:5432/<database>' -v ON_ERROR_STOP=1 -f database/schema.sql
psql 'postgresql://<user>@<host>:5432/<database>' -v ON_ERROR_STOP=1 -f database/seed.sql
psql 'postgresql://<user>@<host>:5432/<database>' -v ON_ERROR_STOP=1 -f '<secure path supplied by the data steward>/shared_data.sql'
Remove-Item Env:PGPASSWORD
```

The private `shared_data.sql` is supplied and imported by the project data
steward. It must contain only approved/shared source data, with roads and zones
loaded before traffic and accident rows. Do not add it to this repository.

## Existing shared database

The database administrator applies both migrations once, then shares the same
connection string with the team. Each migration records its version in
`app_migrations`; readiness checks both markers. Migration 002 repairs hotspot
rows previously blended with checkout-local CSV values:

```powershell
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f database/migrations/001_geocode_suggestion_cache.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f database/migrations/002_rebuild_hotspots_from_shared_records.sql
```

To deliberately refresh provider suggestions for every teammate, the database
administrator may clear the shared provider cache:

```sql
TRUNCATE TABLE geocode_suggestion_cache;
```

## Teammate setup and checks

1. Copy `backend/.env.example` to `backend/.env` and add the shared `DATABASE_URL`
   and a private `JWT_SECRET_KEY`. The chatbot, email, and other optional
   integrations may be left blank. Photon geocoding does not require a key.
2. Install the backend requirements and start the API as described in
   `backend/README.md`.
3. Open `http://127.0.0.1:8000/api/public/readiness`. It must report
   `status: READY`, `database.connected: true`, the expected shared
   `database_target`, non-zero roads, traffic and accidents, and both migration
   checks set to `true`.
4. Start the frontend. It uses `VITE_API_BASE_URL` only to select the backend;
   it contains no provider or database secrets.

`GEOCODING_BBOX` is intentionally ignored. All geocode suggestions are clipped
to the fixed Hyderabad bounding box `(78.20, 17.20, 78.65, 17.60)`. Photon
results are written to `geocode_suggestion_cache` in the shared database, so
backend instances use one provider result for a given query/configuration.
