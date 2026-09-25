from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middlewares
from app.routers import register_routers

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(
    title="RoadSense AI",
    description="AI-Based Smart Traffic & Accident Prediction System",
    version="1.0.0"
)

register_middlewares(app)
register_exception_handlers(app)
register_routers(app)


@app.get("/health", tags=["System Health"], summary="Check API Server Health")
def health():
    return {"status": "healthy"}


@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
@app.get("/forgot-password", include_in_schema=False)
def serve_frontend_spa():
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return {"message": "RoadSense AI API is running"}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
