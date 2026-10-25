CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(64) PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    ticket_count INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_account_created
    ON orders(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_device_created
    ON orders(device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS fraud_decisions (
    order_id VARCHAR(64) PRIMARY KEY REFERENCES orders(order_id),
    risk_score DOUBLE PRECISION NOT NULL,
    decision VARCHAR(16) NOT NULL,
    reasons JSONB NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    scored_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_review_scored
    ON fraud_decisions(decision, scored_at DESC);
