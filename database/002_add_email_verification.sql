-- Run once against the RoadSense AI PostgreSQL database.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE users
    ALTER COLUMN is_email_verified SET DEFAULT FALSE;

CREATE TABLE email_verification_otps (
    otp_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    otp_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_email_verification_otps_user_id
    ON email_verification_otps (user_id);
