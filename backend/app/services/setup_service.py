"""Shared-source readiness checks.

Every developer must run against the same shared PostgreSQL (Supabase) project
and the same committed artifacts. This module reports, in one place, whether the
backend can see that shared configuration so setup problems are obvious instead
of showing up as different suggestions/hotspots on different machines.
"""

import os
from typing import Any, Dict

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database.models import (
    Accident,
    AccidentHotspot,
    Road,
    TrafficRecord,
    TrafficZone,
    GeocodeSuggestionCache,
    SchemaMigration,
)
from app.database.connection import engine
from app.services.geocoding import _geocoding_settings, get_geocoding_bbox

# Tables whose row counts prove the shared project data has been provisioned.
SHARED_SOURCE_TABLES = {
    "roads": Road,
    "traffic_records": TrafficRecord,
    "accidents": Accident,
    "accident_hotspots": AccidentHotspot,
    "traffic_zones": TrafficZone,
    "geocode_suggestion_cache": GeocodeSuggestionCache,
    "app_migrations": SchemaMigration,
}


def _database_report(db: Session) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "configured": bool((os.getenv("DATABASE_URL") or "").strip()),
        "connected": False,
        "schema_ready": False,
        "error": None,
        "counts": {},
    }
    try:
        db.execute(text("SELECT 1"))
        report["connected"] = True
    except Exception as exc:  # noqa: BLE001 - never return connection details
        report["error"] = f"Database connection failed ({type(exc).__name__})."
        return report

    try:
        for name, model in SHARED_SOURCE_TABLES.items():
            report["counts"][name] = int(db.query(func.count()).select_from(model).scalar() or 0)
        report["migrations"] = sorted(
            version for (version,) in db.query(SchemaMigration.version).all()
        )
        report["schema_ready"] = True
    except Exception as exc:  # noqa: BLE001 - surface any driver/config error to the caller
        # Avoid returning connection strings or host-specific driver details.
        report["error"] = f"Database/schema check failed ({type(exc).__name__})."
    return report


def build_readiness_report(db: Session) -> Dict[str, Any]:
    """Return a machine-readable summary of the shared setup state."""
    settings = _geocoding_settings()
    bbox = get_geocoding_bbox()
    database = _database_report(db)

    shared_data_present = all(
        database["counts"].get(name, 0) > 0
        for name in ("roads", "traffic_records", "accidents")
    )
    checks = {
        "database_connected": database["connected"],
        "shared_data_present": database["connected"] and shared_data_present,
        "database_schema_ready": database["schema_ready"],
        "suggestion_cache_ready": database["schema_ready"] and "geocode_suggestion_cache" in database["counts"],
        "suggestion_cache_migration_applied": "001_geocode_suggestion_cache" in database.get("migrations", set()),
        "hotspot_data_migration_applied": "002_rebuild_hotspots_from_shared_records" in database.get("migrations", set()),
    }
    status = "READY" if (
        checks["database_connected"]
        and checks["database_schema_ready"]
        and checks["shared_data_present"]
        and checks["suggestion_cache_ready"]
        and checks["suggestion_cache_migration_applied"]
        and checks["hotspot_data_migration_applied"]
    ) else "DEGRADED"

    # Report database identity for configuration checks without returning
    # usernames, passwords, or the complete connection string.
    database_target = {
        "host": engine.url.host,
        "database": engine.url.database,
    }

    return {
        "status": status,
        "database": database,
        "database_target": database_target,
        "geocoding": {
            "provider": settings["provider"],
            "base_url": settings["base_url"],
            "requires_api_key": False,
            "city": settings["city"],
            "boundary_bbox": list(bbox),
        },
        "traffic_data": {
            "source": "shared database traffic_records",
            "note": "Prediction and traffic observations use the configured project database.",
        },
        "checks": checks,
    }
