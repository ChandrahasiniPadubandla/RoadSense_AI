-- Remove counts/risk scores previously blended from checkout-local CSV data.
-- Recompute persisted zone hotspots from shared accidents and predictions.
WITH accident_counts AS (
    SELECT
        tz.zone_id,
        COUNT(DISTINCT a.accident_id)::INTEGER AS accident_count
    FROM traffic_zones AS tz
    JOIN roads AS r ON r.zone_id = tz.zone_id
    LEFT JOIN accidents AS a ON a.road_id = r.road_id
    GROUP BY tz.zone_id
), prediction_risks AS (
    SELECT
        r.zone_id,
        AVG(ap.risk_percentage) AS avg_risk
    FROM roads AS r
    JOIN accident_predictions AS ap ON ap.road_id = r.road_id
    WHERE r.zone_id IS NOT NULL
    GROUP BY r.zone_id
), zone_stats AS (
    SELECT c.zone_id, c.accident_count, p.avg_risk
    FROM accident_counts AS c
    LEFT JOIN prediction_risks AS p ON p.zone_id = c.zone_id
), authoritative AS (
    SELECT
        zone_id,
        accident_count,
        COALESCE(avg_risk, LEAST(90.0, 35.0 + accident_count * 5.0)) AS risk_score
    FROM zone_stats
)
UPDATE accident_hotspots AS h
SET accident_count = a.accident_count,
    risk_score = ROUND(a.risk_score::NUMERIC, 2),
    risk_level = CASE
        WHEN a.risk_score >= 75.0 THEN 'SEVERE'
        WHEN a.risk_score >= 55.0 THEN 'HIGH'
        WHEN a.risk_score >= 30.0 THEN 'MEDIUM'
        ELSE 'LOW'
    END
FROM authoritative AS a
WHERE h.zone_id = a.zone_id;

CREATE TABLE IF NOT EXISTS app_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO app_migrations (version)
VALUES ('002_rebuild_hotspots_from_shared_records')
ON CONFLICT (version) DO NOTHING;
