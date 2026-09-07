-- Consolidate password-reset and email-verification OTPs into one table.
CREATE TABLE auth_otps (
    otp_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    purpose VARCHAR(30) NOT NULL CHECK (
        purpose IN ('email_verification', 'password_reset')
    ),
    otp_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_auth_otps_user_id_purpose
    ON auth_otps (user_id, purpose);

INSERT INTO auth_otps (otp_id, user_id, purpose, otp_hash, expires_at, created_at)
SELECT otp_id, user_id, 'password_reset', otp_hash, expires_at, created_at
FROM password_reset_otps;

INSERT INTO auth_otps (otp_id, user_id, purpose, otp_hash, expires_at, created_at)
SELECT otp_id, user_id, 'email_verification', otp_hash, expires_at, created_at
FROM email_verification_otps;

DROP TABLE password_reset_otps;
DROP TABLE email_verification_otps;