from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Numeric,
    ForeignKey,
)

from app.database.connection import Base


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class TrafficZone(Base):
    __tablename__ = "traffic_zones"

    zone_id = Column(Integer, primary_key=True)
    zone_name = Column(String(150), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime)


class Road(Base):
    __tablename__ = "roads"

    road_id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey("traffic_zones.zone_id"))
    road_name = Column(String(200), nullable=False)
    road_type = Column(String(100))
    road_capacity = Column(Integer)
    speed_limit = Column(Numeric(6, 2))
    road_condition = Column(String(50))
    number_of_lanes = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)


class TrafficRecord(Base):
    __tablename__ = "traffic_records"

    traffic_id = Column(Integer, primary_key=True)
    road_id = Column(Integer, ForeignKey("roads.road_id"), nullable=False)
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


class Accident(Base):
    __tablename__ = "accidents"

    accident_id = Column(Integer, primary_key=True)
    road_id = Column(Integer, ForeignKey("roads.road_id"), nullable=False)
    accident_datetime = Column(DateTime, nullable=False)
    weather_condition = Column(String(100))
    road_condition = Column(String(50))
    vehicle_count = Column(Integer)
    number_of_vehicles = Column(Integer)
    severity = Column(String(20))
    fatalities = Column(Integer, default=0)
    injuries = Column(Integer, default=0)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime)


class AccidentHotspot(Base):
    __tablename__ = "accident_hotspots"

    hotspot_id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey("traffic_zones.zone_id"))
    accident_count = Column(Integer, default=0)
    risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))
    calculated_at = Column(DateTime)