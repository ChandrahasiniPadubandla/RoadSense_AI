-- Apply to existing project databases. Safe to run more than once.
CREATE TABLE IF NOT EXISTS geocode_suggestion_cache (
    cache_key VARCHAR(64) PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO app_migrations (version)
VALUES ('001_geocode_suggestion_cache')
ON CONFLICT (version) DO NOTHING;
