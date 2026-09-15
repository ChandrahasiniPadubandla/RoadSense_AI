from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.security import get_current_user
from app.database.connection import get_db
from app.database.models import AccidentHotspot, Accident

from app.routers import zones
from app.routers import roads
from app.routers import traffic
from app.routers import accidents
from app.routers import dashboard
from app.routers import maps
from app.routers import admin
from app.routers import audit
from app.routers import weather
from app.routers import chatbot
from app.routers import traffic_predictions
from app.routers import accident_predictions
from app.routers import alert
from app.routers import geocoding
from app.routers import emergency
from app.routers import ml
from app.routers import anomaly
from app.routers import accident_hotspots
from app.routers import reports

from app.routers.auth import router as auth_router


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


app = FastAPI(
    title="RoadSense AI",
    description="AI-Based Smart Traffic & Accident Prediction System",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API ROUTERS
# ============================================================

# Authentication
app.include_router(auth_router)

# Chatbot
app.include_router(chatbot.router)

# Geocoding & Routing
app.include_router(geocoding.router)

# Real-Time Weather Telemetry
app.include_router(weather.router)

# Emergency Dispatch
app.include_router(
    emergency.router,
    dependencies=[Depends(get_current_user)]
)

# Alerts
app.include_router(
    alert.router,
    dependencies=[Depends(get_current_user)]
)
app.include_router(
    alert.router,
    prefix="/api",
    dependencies=[Depends(get_current_user)]
)

# Zones
app.include_router(
    zones.router,
    dependencies=[Depends(get_current_user)]
)

# Roads
app.include_router(
    roads.router,
    dependencies=[Depends(get_current_user)]
)

# Traffic Records & Sensor Feeds
app.include_router(
    traffic.router,
    dependencies=[Depends(get_current_user)]
)

# Accident Incidents
app.include_router(
    accidents.router,
    dependencies=[Depends(get_current_user)]
)

# Dashboard Analytics
app.include_router(
    dashboard.router,
    dependencies=[Depends(get_current_user)]
)

# Maps
app.include_router(
    maps.router,
    dependencies=[Depends(get_current_user)]
)

# Admin Management
app.include_router(
    admin.router,
    dependencies=[Depends(get_current_user)]
)

# Audit Logs
app.include_router(
    audit.router,
    dependencies=[Depends(get_current_user)]
)

# Traffic Predictions (AI)
app.include_router(
    traffic_predictions.router,
    dependencies=[Depends(get_current_user)]
)

# Accident Risk Predictions (AI)
app.include_router(
    accident_predictions.router,
    dependencies=[Depends(get_current_user)]
)

# Reports & Analytics Export (SUPER_ADMIN & TRAFFIC_AUTHORITY)
app.include_router(
    reports.router
)

# ML integration endpoints currently use deterministic placeholders.
app.include_router(
    ml.router,
    prefix="/api/ml"
)
app.include_router(
    anomaly.router,
    prefix="/api/anomaly"
)
app.include_router(
    accident_hotspots.router,
    prefix="/api/hotspots"
)


# ============================================================
# ACCIDENT HOTSPOTS
# ============================================================

@app.get(
    "/api/hotspots",
    tags=["Hotspots"]
)
def get_hotspots_list(
    db: Session = Depends(get_db)
):
    hotspots = db.query(AccidentHotspot).all()

    if hotspots:
        return [
            {
                "road_id": str(
                    h.zone_id or h.hotspot_id
                ),
                "hotspot_id": str(h.hotspot_id),
                "accident_count": h.accident_count or 0,
                "risk_level": h.risk_level or "MODERATE"
            }
            for h in hotspots
        ]

    accidents = db.query(Accident).limit(20).all()

    if accidents:
        return [
            {
                "road_id": str(a.road_id),
                "hotspot_id": str(a.accident_id),
                "accident_count": 1,
                "risk_level": a.severity or "MODERATE"
            }
            for a in accidents
        ]

    return []


# ============================================================
# ROOT / FRONTEND
# ============================================================

@app.get("/", include_in_schema=False)
def root():
    frontend_index = FRONTEND_DIST / "index.html"

    if frontend_index.exists():
        return FileResponse(frontend_index)

    return {
        "message": "RoadSense AI API is running"
    }


@app.get("/login", include_in_schema=False)
def login_page():
    frontend_index = FRONTEND_DIST / "index.html"

    if frontend_index.exists():
        return FileResponse(frontend_index)

    return {
        "message": "RoadSense AI API is running"
    }


@app.get("/forgot-password", include_in_schema=False)
def forgot_password_page():
    frontend_index = FRONTEND_DIST / "index.html"

    if frontend_index.exists():
        return FileResponse(frontend_index)

    return {
        "message": "RoadSense AI API is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/health",
    tags=["System Health"],
    summary="Check API Server Health"
)
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# SERVE FRONTEND
# ============================================================

if FRONTEND_DIST.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=FRONTEND_DIST,
            html=True
        ),
        name="frontend"
    )
