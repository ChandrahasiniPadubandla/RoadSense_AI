"""Compatibility imports for the application's SQLAlchemy models.

All table mappings live in :mod:`app.database.models`. Keeping only one
mapping for each table is required because every model shares the same
SQLAlchemy ``Base.metadata`` instance.
"""

from app.database.models import (
    Accident,
    AccidentHotspot,
    AuthOTP,
    AuditLog,
    Road,
    Role,
    TrafficRecord,
    TrafficZone,
    User,
    WeatherRecord,
)

__all__ = [
    "Accident",
    "AccidentHotspot",
    "AuthOTP",
    "AuditLog",
    "Road",
    "Role",
    "TrafficRecord",
    "TrafficZone",
    "User",
    "WeatherRecord",
]
