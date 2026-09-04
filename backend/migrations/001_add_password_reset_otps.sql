-- Run once against the RoadSense AI PostgreSQL database.
CREATE TABLE password_reset_otps (
    otp_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    otp_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_password_reset_otps_user_id
    ON password_reset_otps (user_id);
