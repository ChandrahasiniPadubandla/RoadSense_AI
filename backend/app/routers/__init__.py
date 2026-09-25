from fastapi import FastAPI, Depends

from app.security import get_current_user
from app.routers.auth import router as auth_router
from app.routers import (
    chatbot,
    geocoding,
    weather,
    telemetry,
    reports,
    anomaly,
    emergency,
    alert,
    zones,
    roads,
    traffic,
    accidents,
    dashboard,
    maps,
    admin,
    audit,
    traffic_predictions,
    accident_predictions,
    accident_hotspots,
)


def register_routers(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(chatbot.router)
    app.include_router(geocoding.router)
    app.include_router(weather.router)
    app.include_router(telemetry.router)
    app.include_router(reports.router)
    app.include_router(anomaly.router)

    auth_dep = [Depends(get_current_user)]

    app.include_router(emergency.router, dependencies=auth_dep)
    app.include_router(alert.router, dependencies=auth_dep)
    app.include_router(zones.router, dependencies=auth_dep)
    app.include_router(roads.router, dependencies=auth_dep)
    app.include_router(traffic.router, dependencies=auth_dep)
    app.include_router(accidents.router, dependencies=auth_dep)
    app.include_router(dashboard.router, dependencies=auth_dep)
    app.include_router(maps.router, dependencies=auth_dep)
    app.include_router(admin.router, dependencies=auth_dep)
    app.include_router(audit.router, dependencies=auth_dep)
    app.include_router(traffic_predictions.router, dependencies=auth_dep)
    app.include_router(accident_predictions.router, dependencies=auth_dep)
    app.include_router(accident_hotspots.router, dependencies=auth_dep)
