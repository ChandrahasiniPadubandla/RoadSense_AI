import uuid
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Numeric, Uuid
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography

from app.database.connection import Base


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    role_id = Column(Uuid, ForeignKey("roles.role_id"), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    otp_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User")


class TrafficZone(Base):
    __tablename__ = "traffic_zones"

    zone_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)

    zone_name = Column(String(150), nullable=False)

    description = Column(Text)

    location = Column(
        Geography(
            geometry_type="POINT",
            srid=4326
        )
    )

    created_at = Column(DateTime)


class Road(Base):
    __tablename__ = "roads"

    road_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)

    zone_id = Column(
        Uuid,
        ForeignKey("traffic_zones.zone_id")
    )

    start_location = Column(
        Geography(
            geometry_type="POINT",
            srid=4326
        )
    )

    end_location = Column(
        Geography(
            geometry_type="POINT",
            srid=4326
        )
    )

    road_name = Column(String(200), nullable=False)

    road_type = Column(String(100))

    road_capacity = Column(Integer)

    speed_limit = Column(Numeric(6, 2))

    road_condition = Column(String(50))

    number_of_lanes = Column(Integer)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime)

    zone = relationship("TrafficZone")


class TrafficRecord(Base):

    __tablename__ = "traffic_records"

    traffic_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)

    road_id = Column(
        Uuid,
        ForeignKey("roads.road_id"),
        nullable=False
    )

    timestamp = Column(DateTime, nullable=False)

    vehicle_count = Column(Integer, nullable=False)

    average_speed = Column(Numeric(6, 2))

    traffic_density = Column(Numeric(6, 2))

    congestion_level = Column(String(20))

    road_condition = Column(String(50))

    weather_condition = Column(String(100))

    rainfall = Column(Numeric(7, 2))

    temperature = Column(Numeric(5, 2))

    visibility = Column(Numeric(7, 2))

    is_holiday = Column(Boolean, default=False)

    road = relationship("Road")

class Accident(Base):
    __tablename__ = "accidents"

    accident_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)

    road_id = Column(
        Uuid,
        ForeignKey("roads.road_id"),
        nullable=False
    )

    location = Column(
        Geography(
            geometry_type="POINT",
            srid=4326
        )
    )

    accident_datetime = Column(DateTime, nullable=False)

    weather_condition = Column(String(100))

    road_condition = Column(String(50))

    vehicle_count = Column(Integer)

    number_of_vehicles = Column(Integer)

    severity = Column(String(20))

    fatalities = Column(Integer, default=0)

    injuries = Column(Integer, default=0)

    description = Column(Text)

    created_by = Column(
        Uuid,
        ForeignKey("users.user_id")
    )

    created_at = Column(DateTime)

    road = relationship("Road")


class AccidentHotspot(Base):
    __tablename__ = "accident_hotspots"

    hotspot_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    zone_id = Column(Uuid, ForeignKey("traffic_zones.zone_id"))
    location = Column(Geography(geometry_type="POINT", srid=4326))
    accident_count = Column(Integer, default=0)
    risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))
    calculated_at = Column(DateTime)
