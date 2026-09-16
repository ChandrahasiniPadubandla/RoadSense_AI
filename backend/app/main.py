from pathlib import Path

from fastapi import FastAPI, Depends, Request
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
# API PREFIX COMPATIBILITY (TRANSPARENT REWRITE FOR /api/* CALLS)
# ============================================================

@app.middleware("http")
async def api_prefix_compatibility_middleware(request: Request, call_next):
    path = request.scope.get("path", "")
    if path.startswith("/api/"):
        request.scope["path"] = path[4:]
    return await call_next(request)


# ============================================================
# GLOBAL EXCEPTION HANDLERS (STRUCTURED DIAGNOSTICS & CORS SAFE)
# ============================================================

import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("roadsense")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("issue") or detail.get("error") or str(detail)
        error_code = detail.get("error_code") or f"HTTP_{exc.status_code}"
    else:
        message = str(detail)
        error_code = f"HTTP_{exc.status_code}"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_code": error_code,
            "message": message,
            "detail": message,
            "diagnostic_data": detail if isinstance(detail, dict) else None
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


from fastapi.encoders import jsonable_encoder
import re


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_body = None
    try:
        raw_body = await request.body()
    except Exception:
        pass

    error_messages = []
    for err in exc.errors():
        err_type = err.get("type")
        msg = err.get("msg", "Invalid value")
        ctx = err.get("ctx", {})
        ctx_error = ctx.get("error", "")
        if isinstance(ctx_error, Exception):
            ctx_error = str(ctx_error)

        if err_type == "json_invalid":
            loc = err.get("loc", ())
            offset = next((item for item in loc if isinstance(item, int)), None)

            suspect_field = None
            if raw_body and offset is not None:
                try:
                    prefix = raw_body[:offset].decode("utf-8", errors="replace")
                    keys = re.findall(r'"([a-zA-Z0-9_]+)"\s*:', prefix)
                    if keys:
                        suspect_field = keys[-1]
                except Exception:
                    pass

            detail_msg = "Malformed JSON syntax in request body"
            if offset is not None:
                detail_msg += f" at character position {offset}"
            if suspect_field:
                detail_msg += f" (in or near field '{suspect_field}')"
            if ctx_error:
                detail_msg += f": {ctx_error}"
            else:
                detail_msg += f": {msg}"

            if suspect_field in ("password", "new_password", "newPassword") or "control character" in str(ctx_error).lower():
                detail_msg += ". Please verify that your password or text does not contain raw unescaped line breaks, tabs, or quotes."

            error_messages.append(detail_msg)
        else:
            field = " -> ".join(str(loc) for loc in err.get("loc", []) if loc != "body")
            clean_msg = msg.replace("Value error, ", "")
            error_messages.append(f"{field}: {clean_msg}" if field else clean_msg)

    combined_message = "; ".join(error_messages) or "Validation failed"

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": f"Validation failed: {combined_message}",
            "detail": combined_message,
            "errors": jsonable_encoder(exc.errors())
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s: %s\n%s", request.method, request.url.path, exc, tb)

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": f"Server error: {str(exc)}",
            "detail": f"Server error processing request: {str(exc)}"
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
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
    prefix="/ml"
)
app.include_router(
    anomaly.router,
    prefix="/anomaly"
)
app.include_router(
    accident_hotspots.router,
    prefix="/hotspots"
)


# ============================================================
# ACCIDENT HOTSPOTS
# ============================================================

@app.get(
    "/hotspots",
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
