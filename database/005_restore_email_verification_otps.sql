-- Restore email-verification OTP support in the shared OTP table.
ALTER TABLE auth_otps
    DROP CONSTRAINT IF EXISTS auth_otps_purpose_check;

ALTER TABLE auth_otps
    ADD CONSTRAINT auth_otps_purpose_check
    CHECK (purpose IN ('email_verification', 'password_reset'));