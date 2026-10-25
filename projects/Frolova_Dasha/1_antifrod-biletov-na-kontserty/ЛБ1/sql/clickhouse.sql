CREATE TABLE IF NOT EXISTS antifraud_events (
    event_date Date,
    scored_at DateTime,
    order_id String,
    event_id String,
    decision LowCardinality(String),
    risk_score Float64,
    model_version LowCardinality(String),
    reason_codes Array(String)
) ENGINE = MergeTree
PARTITION BY event_date
ORDER BY (event_date, decision, order_id);
