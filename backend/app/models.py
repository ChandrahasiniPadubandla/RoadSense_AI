"""Compatibility imports for the application's SQLAlchemy models.

All table mappings live in :mod:`app.database.models`. Keeping only one
mapping for each table is required because every model shares the same
SQLAlchemy ``Base.metadata`` instance.
"""

from app.database.models import (
    Accident,
    AccidentHotspot,
    AuthOTP,
    Road,
    Role,
    TrafficRecord,
    TrafficZone,
    User,
)

__all__ = [
    "Accident",
    "AccidentHotspot",
    "AuthOTP",
    "Road",
    "Role",
    "TrafficRecord",
    "TrafficZone",
    "User",
]
