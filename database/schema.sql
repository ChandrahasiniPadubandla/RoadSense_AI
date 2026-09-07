-- =========================================================
-- AI-BASED SMART TRAFFIC & ACCIDENT PREDICTION SYSTEM
-- PostgreSQL + PostGIS Database
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================================
-- 1. ROLES
-- =========================================================

CREATE TABLE roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    role_name VARCHAR(50) UNIQUE NOT NULL,

    description TEXT
);


-- =========================================================
-- 2. USERS
-- =========================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    role_id UUID NOT NULL,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) UNIQUE NOT NULL,

    password_hash TEXT NOT NULL,

    phone VARCHAR(20),

    is_active BOOLEAN DEFAULT TRUE,

    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
);


-- =========================================================
-- 2.1 AUTHENTICATION OTPs
-- =========================================================

CREATE TABLE auth_otps (
    otp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    purpose VARCHAR(30) NOT NULL CHECK (
        purpose IN ('email_verification', 'password_reset')
    ),

    otp_hash VARCHAR(64) NOT NULL,

    expires_at TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_auth_otp_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE INDEX ix_auth_otps_user_id_purpose
    ON auth_otps (user_id, purpose);


-- =========================================================
-- 3. TRAFFIC ZONES
-- =========================================================

CREATE TABLE traffic_zones (
    zone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    zone_name VARCHAR(150) NOT NULL,

    description TEXT,

    location GEOGRAPHY(POINT, 4326),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 4. ROADS
-- =========================================================

CREATE TABLE roads (
    road_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    zone_id UUID,

    road_name VARCHAR(200) NOT NULL,

    road_type VARCHAR(100),

    start_location GEOGRAPHY(POINT, 4326),

    end_location GEOGRAPHY(POINT, 4326),

    road_capacity INTEGER,

    speed_limit DECIMAL(6,2),

    road_condition VARCHAR(50),

    number_of_lanes INTEGER,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_road_zone
        FOREIGN KEY (zone_id)
        REFERENCES traffic_zones(zone_id)
);


-- =========================================================
-- 5. WEATHER RECORDS
-- =========================================================

CREATE TABLE weather_records (
    weather_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID NOT NULL,

    timestamp TIMESTAMP NOT NULL,

    temperature DECIMAL(5,2),

    rainfall DECIMAL(7,2),

    humidity DECIMAL(5,2),

    visibility DECIMAL(7,2),

    wind_speed DECIMAL(7,2),

    weather_condition VARCHAR(100),

    CONSTRAINT fk_weather_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id)
);


-- =========================================================
-- 6. TRAFFIC RECORDS
-- =========================================================

CREATE TABLE traffic_records (
    traffic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID NOT NULL,

    timestamp TIMESTAMP NOT NULL,

    vehicle_count INTEGER NOT NULL,

    average_speed DECIMAL(6,2),

    traffic_density DECIMAL(6,2),

    congestion_level VARCHAR(20),

    road_condition VARCHAR(50),

    weather_condition VARCHAR(100),

    rainfall DECIMAL(7,2),

    temperature DECIMAL(5,2),

    visibility DECIMAL(7,2),

    is_holiday BOOLEAN DEFAULT FALSE,

    CONSTRAINT fk_traffic_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id)
);


-- =========================================================
-- 7. ACCIDENTS
-- =========================================================

CREATE TABLE accidents (
    accident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID NOT NULL,

    location GEOGRAPHY(POINT, 4326),

    accident_datetime TIMESTAMP NOT NULL,

    weather_condition VARCHAR(100),

    road_condition VARCHAR(50),

    vehicle_count INTEGER,

    number_of_vehicles INTEGER,

    severity VARCHAR(20),

    fatalities INTEGER DEFAULT 0,

    injuries INTEGER DEFAULT 0,

    description TEXT,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_accident_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id),

    CONSTRAINT fk_accident_user
        FOREIGN KEY (created_by)
        REFERENCES users(user_id)
);


-- =========================================================
-- 8. ML MODEL VERSIONS
-- =========================================================

CREATE TABLE model_versions (
    model_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    model_name VARCHAR(100) NOT NULL,

    model_type VARCHAR(100),

    version VARCHAR(50),

    algorithm VARCHAR(100),

    accuracy DECIMAL(5,2),

    precision_score DECIMAL(5,2),

    recall_score DECIMAL(5,2),

    f1_score DECIMAL(5,2),

    trained_at TIMESTAMP,

    is_active BOOLEAN DEFAULT TRUE
);


-- =========================================================
-- 9. TRAFFIC PREDICTIONS
-- =========================================================

CREATE TABLE traffic_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID NOT NULL,

    prediction_time TIMESTAMP NOT NULL,

    target_time TIMESTAMP NOT NULL,

    predicted_congestion VARCHAR(20),

    predicted_vehicle_count INTEGER,

    confidence_score DECIMAL(5,2),

    model_version_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_traffic_prediction_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id),

    CONSTRAINT fk_traffic_prediction_model
        FOREIGN KEY (model_version_id)
        REFERENCES model_versions(model_version_id)
);


-- =========================================================
-- 10. ACCIDENT PREDICTIONS
-- =========================================================

CREATE TABLE accident_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID NOT NULL,

    prediction_time TIMESTAMP NOT NULL,

    risk_percentage DECIMAL(5,2),

    risk_level VARCHAR(20),

    confidence_score DECIMAL(5,2),

    model_version_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_accident_prediction_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id),

    CONSTRAINT fk_accident_prediction_model
        FOREIGN KEY (model_version_id)
        REFERENCES model_versions(model_version_id)
);


-- =========================================================
-- 11. ACCIDENT HOTSPOTS
-- =========================================================

CREATE TABLE accident_hotspots (
    hotspot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    zone_id UUID,

    location GEOGRAPHY(POINT, 4326),

    accident_count INTEGER DEFAULT 0,

    risk_score DECIMAL(5,2),

    risk_level VARCHAR(20),

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_hotspot_zone
        FOREIGN KEY (zone_id)
        REFERENCES traffic_zones(zone_id)
);


-- =========================================================
-- 12. TRAFFIC ANOMALIES
-- =========================================================

CREATE TABLE traffic_anomalies (
    anomaly_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID NOT NULL,

    traffic_id UUID,

    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    normal_vehicle_count INTEGER,

    actual_vehicle_count INTEGER,

    anomaly_score DECIMAL(6,2),

    anomaly_type VARCHAR(50),

    description TEXT,

    status VARCHAR(30) DEFAULT 'ACTIVE',

    CONSTRAINT fk_anomaly_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id),

    CONSTRAINT fk_anomaly_traffic
        FOREIGN KEY (traffic_id)
        REFERENCES traffic_records(traffic_id)
);


-- =========================================================
-- 13. ALERTS
-- =========================================================

CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    road_id UUID,

    prediction_id UUID,

    alert_type VARCHAR(50),

    severity VARCHAR(20),

    message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(30) DEFAULT 'ACTIVE',

    resolved_at TIMESTAMP,

    CONSTRAINT fk_alert_road
        FOREIGN KEY (road_id)
        REFERENCES roads(road_id)
);


-- =========================================================
-- 14. EMERGENCY RESPONSES
-- =========================================================

CREATE TABLE emergency_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    accident_id UUID NOT NULL,

    assigned_user_id UUID,

    response_status VARCHAR(30) DEFAULT 'PENDING',

    assigned_at TIMESTAMP,

    arrived_at TIMESTAMP,

    resolved_at TIMESTAMP,

    notes TEXT,

    CONSTRAINT fk_response_accident
        FOREIGN KEY (accident_id)
        REFERENCES accidents(accident_id),

    CONSTRAINT fk_response_user
        FOREIGN KEY (assigned_user_id)
        REFERENCES users(user_id)
);


-- =========================================================
-- 15. AUDIT LOGS
-- =========================================================

CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID,

    action VARCHAR(50),

    entity_type VARCHAR(100),

    entity_id UUID,

    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(50),

    details TEXT,

    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);


-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_traffic_road
ON traffic_records(road_id);

CREATE INDEX idx_traffic_timestamp
ON traffic_records(timestamp);

CREATE INDEX idx_accidents_road
ON accidents(road_id);

CREATE INDEX idx_accidents_datetime
ON accidents(accident_datetime);

CREATE INDEX idx_predictions_road
ON traffic_predictions(road_id);

CREATE INDEX idx_accident_predictions_road
ON accident_predictions(road_id);