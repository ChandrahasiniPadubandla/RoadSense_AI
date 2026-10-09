import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middlewares
from app.routers import register_routers

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

logger = logging.getLogger("Metrivon.startup")


def _log_startup_readiness() -> None:
    """Log whether the shared database/artifacts are visible. Never fatal."""
    try:
        from app.database.connection import SessionLocal
        from app.services.setup_service import build_readiness_report

        db = SessionLocal()
        try:
            report = build_readiness_report(db)
        finally:
            db.close()

        counts = report["database"]["counts"]
        if report["status"] == "READY":
            logger.info(
                "Startup readiness READY | roads=%s traffic=%s accidents=%s hotspots=%s | bbox=%s",
                counts.get("roads"),
                counts.get("traffic_records"),
                counts.get("accidents"),
                counts.get("accident_hotspots"),
                report["geocoding"]["boundary_bbox"],
            )
        else:
            logger.warning(
                "Startup readiness DEGRADED | db_connected=%s shared_data=%s error=%s",
                report["checks"]["database_connected"],
                report["checks"]["shared_data_present"],
                report["database"]["error"],
            )
    except Exception as exc:  # noqa: BLE001 - diagnostics must never block startup
        logger.warning("Startup readiness check could not run: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log_startup_readiness()
    yield


app = FastAPI(
    title="Metrivon AI",
    description="AI-Based Smart Traffic & Accident Prediction System",
    version="1.0.0",
    lifespan=lifespan,
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
    return {"message": "Metrivon AI API is running"}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
