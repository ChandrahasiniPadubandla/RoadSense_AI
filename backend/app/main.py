from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.security import get_current_user
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
from app.routers import predictions
from app.routers.auth import router as auth_router

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

app.include_router(
    chatbot.router
)

app.include_router(
    zones.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    roads.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    traffic.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    accidents.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    dashboard.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    maps.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    weather.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    admin.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    audit.router,
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    predictions.router,
    dependencies=[Depends(get_current_user)]
)

@app.get("/")
def root():

    return {
        "message": "RoadSense AI API is running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }