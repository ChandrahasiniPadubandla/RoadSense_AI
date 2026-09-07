import uuid
from datetime import datetime
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
    is_email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    role = relationship("Role")


class AuthOTP(Base):
    __tablename__ = "auth_otps"

    otp_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(30), nullable=False, index=True)
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


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    weather_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    road_id = Column(Uuid, ForeignKey("roads.road_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    temperature = Column(Numeric(5, 2))
    rainfall = Column(Numeric(7, 2))
    humidity = Column(Numeric(5, 2))
    visibility = Column(Numeric(7, 2))
    wind_speed = Column(Numeric(7, 2))
    weather_condition = Column(String(100))

    road = relationship("Road")


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


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    road_id = Column(Uuid, ForeignKey("roads.road_id"))
    prediction_id = Column(Uuid)
    alert_type = Column(String(50))
    severity = Column(String(20))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(30), default="ACTIVE")
    resolved_at = Column(DateTime)

    road = relationship("Road")


class TrafficAnomaly(Base):
    __tablename__ = "traffic_anomalies"

    anomaly_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    road_id = Column(Uuid, ForeignKey("roads.road_id"), nullable=False)
    traffic_id = Column(Uuid, ForeignKey("traffic_records.traffic_id"))
    detected_at = Column(DateTime, default=datetime.utcnow)
    normal_vehicle_count = Column(Integer)
    actual_vehicle_count = Column(Integer)
    anomaly_score = Column(Numeric(6, 2))
    anomaly_type = Column(String(50))
    description = Column(Text)
    status = Column(String(30), default="ACTIVE")

    road = relationship("Road")
    traffic_record = relationship("TrafficRecord")


class EmergencyResponse(Base):
    __tablename__ = "emergency_responses"

    response_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    accident_id = Column(Uuid, ForeignKey("accidents.accident_id"), nullable=False)
    assigned_user_id = Column(Uuid, ForeignKey("users.user_id"))
    response_status = Column(String(30), default="PENDING")
    assigned_at = Column(DateTime)
    arrived_at = Column(DateTime)
    resolved_at = Column(DateTime)
    notes = Column(Text)

    accident = relationship("Accident")
    assigned_user = relationship("User")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    model_version_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(100))
    version = Column(String(50))
    algorithm = Column(String(100))
    accuracy = Column(Numeric(5, 2))
    precision_score = Column(Numeric(5, 2))
    recall_score = Column(Numeric(5, 2))
    f1_score = Column(Numeric(5, 2))
    trained_at = Column(DateTime)
    is_active = Column(Boolean, default=True)


class TrafficPrediction(Base):
    __tablename__ = "traffic_predictions"

    prediction_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    road_id = Column(Uuid, ForeignKey("roads.road_id"), nullable=False)
    prediction_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    target_time = Column(DateTime, nullable=False)
    predicted_congestion = Column(String(20))
    predicted_vehicle_count = Column(Integer)
    confidence_score = Column(Numeric(5, 2))
    model_version_id = Column(Uuid, ForeignKey("model_versions.model_version_id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    road = relationship("Road")
    model_version = relationship("ModelVersion")


class AccidentPrediction(Base):
    __tablename__ = "accident_predictions"

    prediction_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    road_id = Column(Uuid, ForeignKey("roads.road_id"), nullable=False)
    prediction_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    risk_percentage = Column(Numeric(5, 2))
    risk_level = Column(String(20))
    confidence_score = Column(Numeric(5, 2))
    model_version_id = Column(Uuid, ForeignKey("model_versions.model_version_id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    road = relationship("Road")
    model_version = relationship("ModelVersion")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    weather_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    road_id = Column(Uuid, ForeignKey("roads.road_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    temperature = Column(Numeric(5, 2))
    rainfall = Column(Numeric(7, 2))
    humidity = Column(Numeric(5, 2))
    visibility = Column(Numeric(7, 2))
    wind_speed = Column(Numeric(7, 2))
    weather_condition = Column(String(100))

    road = relationship("Road")



class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.user_id"))
    action = Column(String(50))
    entity_type = Column(String(100))
    entity_id = Column(Uuid)
    timestamp = Column(DateTime)
    ip_address = Column(String(50))
    details = Column(Text)

    user = relationship("User")
