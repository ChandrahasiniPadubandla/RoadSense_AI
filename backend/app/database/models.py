from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography

from app.database.connection import Base


class TrafficZone(Base):
    __tablename__ = "traffic_zones"

    zone_id = Column(Integer, primary_key=True, index=True)

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

    road_id = Column(Integer, primary_key=True, index=True)

    zone_id = Column(
        Integer,
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

    traffic_id = Column(Integer, primary_key=True, index=True)

    road_id = Column(
        Integer,
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

class User(Base):
    __tablename__ = "users"

    user_id = Column(
        Integer,
        primary_key=True,
        index=True
    )
class Accident(Base):
    __tablename__ = "accidents"

    accident_id = Column(Integer, primary_key=True, index=True)

    road_id = Column(
        Integer,
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
        Integer,
        ForeignKey("users.user_id")
    )

    created_at = Column(DateTime)

    road = relationship("Road")