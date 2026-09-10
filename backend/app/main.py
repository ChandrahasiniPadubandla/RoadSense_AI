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
from app.routers.auth import router as auth_router

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(
    title="RoadSense AI",
    description="AI-Based Smart Traffic & Accident Prediction System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chatbot.router)
app.include_router(alert.router, dependencies=[Depends(get_current_user)])
app.include_router(zones.router, dependencies=[Depends(get_current_user)])
app.include_router(roads.router, dependencies=[Depends(get_current_user)])
app.include_router(traffic.router, dependencies=[Depends(get_current_user)])
app.include_router(accidents.router, dependencies=[Depends(get_current_user)])
app.include_router(dashboard.router, dependencies=[Depends(get_current_user)])
app.include_router(maps.router, dependencies=[Depends(get_current_user)])
app.include_router(weather.router, dependencies=[Depends(get_current_user)])
app.include_router(admin.router, dependencies=[Depends(get_current_user)])
app.include_router(audit.router, dependencies=[Depends(get_current_user)])
app.include_router(traffic_predictions.router, dependencies=[Depends(get_current_user)])
app.include_router(accident_predictions.router, dependencies=[Depends(get_current_user)])


@app.get("/api/hotspots", tags=["Hotspots"])
def get_hotspots_list(db: Session = Depends(get_db)):
    hotspots = db.query(AccidentHotspot).all()
    if hotspots:
        return [
            {
                "road_id": str(h.zone_id or h.hotspot_id),
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

    return [
        {"road_id": "road-secunderabad-01", "hotspot_id": "hs-01", "accident_count": 4, "risk_level": "HIGH"},
        {"road_id": "road-hitec-city-02", "hotspot_id": "hs-02", "accident_count": 2, "risk_level": "MODERATE"},
        {"road_id": "road-begumpet-03", "hotspot_id": "hs-03", "accident_count": 5, "risk_level": "CRITICAL"},
        {"road_id": "road-banjara-hills-04", "hotspot_id": "hs-04", "accident_count": 1, "risk_level": "LOW"}
    ]


@app.get("/")
def root():
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {"message": "RoadSense AI API is running"}


@app.get("/login")
def login_page():
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {"message": "RoadSense AI API is running"}


@app.get("/forgot-password")
def forgot_password_page():
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {"message": "RoadSense AI API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
