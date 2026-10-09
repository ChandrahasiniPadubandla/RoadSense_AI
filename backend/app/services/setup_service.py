"""Shared-source readiness checks.

Every developer must run against the same shared PostgreSQL (Supabase) project
and the same committed artifacts. This module reports, in one place, whether the
backend can see that shared configuration so setup problems are obvious instead
of showing up as different suggestions/hotspots on different machines.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger("Metrivon.setup")

from app.database.models import (
    Accident,
    AccidentHotspot,
    Road,
    TrafficRecord,
    TrafficZone,
)
from app.services.geocoding import _geocoding_settings, get_geocoding_bbox

# Tables whose row counts prove the shared project data has been provisioned.
SHARED_SOURCE_TABLES = {
    "roads": Road,
    "traffic_records": TrafficRecord,
    "accidents": Accident,
    "accident_hotspots": AccidentHotspot,
    "traffic_zones": TrafficZone,
}


def _database_report(db: Session) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "configured": bool((os.getenv("DATABASE_URL") or "").strip()),
        "connected": False,
        "error": None,
        "counts": {},
    }
    try:
        for name, model in SHARED_SOURCE_TABLES.items():
            report["counts"][name] = int(db.query(func.count()).select_from(model).scalar() or 0)
        report["connected"] = True
    except Exception as exc:  # noqa: BLE001 - surface any driver/config error to the caller
        report["error"] = str(exc)
    return report


def _voice_model_path() -> Optional[Path]:
    try:
        from app.services.voice_service import resolve_model_path

        return resolve_model_path()
    except Exception as exc:  # noqa: BLE001 - voice stack must not break readiness
        logger.warning("Voice model resolution unavailable: %s", exc)
        return None


def build_readiness_report(db: Session) -> Dict[str, Any]:
    """Return a machine-readable summary of the shared setup state."""
    settings = _geocoding_settings()
    bbox = get_geocoding_bbox()
    database = _database_report(db)
    voice_path = _voice_model_path()

    shared_rows = sum(database["counts"].get(name, 0) for name in ("roads", "traffic_records", "accidents"))
    checks = {
        "database_connected": database["connected"],
        "shared_data_present": database["connected"] and shared_rows > 0,
        "voice_model_available": bool(voice_path and Path(voice_path).exists()),
        "live_traffic_key_configured": bool((os.getenv("TOMTOM_API_KEY") or "").strip()),
    }
    status = "READY" if (checks["database_connected"] and checks["shared_data_present"]) else "DEGRADED"

    return {
        "status": status,
        "database": database,
        "geocoding": {
            "provider": settings["provider"],
            "base_url": settings["base_url"],
            "api_key_configured": bool(settings["api_key"]),
            "city": settings["city"],
            "boundary_bbox": list(bbox),
        },
        "voice_ner": {
            "model_path": str(voice_path) if voice_path else None,
            "available": checks["voice_model_available"],
        },
        "live_traffic": {
            "provider": "tomtom",
            "api_key_configured": checks["live_traffic_key_configured"],
            "note": "Optional live enrichment. The shared source of traffic data is the traffic_records table.",
        },
        "checks": checks,
    }
