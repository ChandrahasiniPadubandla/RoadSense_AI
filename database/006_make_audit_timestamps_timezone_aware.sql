-- Store login and logout timestamps with timezone information.
ALTER TABLE audit_logs
    ALTER COLUMN timestamp TYPE TIMESTAMPTZ
    USING timestamp AT TIME ZONE 'UTC';

ALTER TABLE audit_logs
    ALTER COLUMN timestamp SET NOT NULL;

ALTER TABLE audit_logs
    ALTER COLUMN timestamp SET DEFAULT CURRENT_TIMESTAMP;