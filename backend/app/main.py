from fastapi import FastAPI

from app.routers import zones
from app.routers import roads
from app.routers import traffic
from app.routers import accidents


app = FastAPI(
    title="RoadSense AI",
    description="AI-Based Smart Traffic & Accident Prediction System",
    version="1.0.0"
)


app.include_router(zones.router)

app.include_router(roads.router)

app.include_router(traffic.router)

app.include_router(accidents.router)


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