CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    algorithm     TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS episodes (
    id            BIGSERIAL PRIMARY KEY,
    experiment_id TEXT        NOT NULL,
    run_id        TEXT,
    episode       INTEGER     NOT NULL,
    steps         INTEGER     NOT NULL,
    reward        REAL        NOT NULL,
    epsilon       REAL,
    loss          REAL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id            BIGSERIAL PRIMARY KEY,
    experiment_id TEXT        NOT NULL,
    run_id        TEXT,
    step          INTEGER     NOT NULL,
    artifact_uri  TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inference_logs (
    id          BIGSERIAL PRIMARY KEY,
    request_id  TEXT        NOT NULL,
    model_name  TEXT,
    action      INTEGER     NOT NULL,
    action_name TEXT,
    latency_ms  REAL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_exp_episode
    ON episodes (experiment_id, episode DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_created
    ON episodes (created_at);
CREATE INDEX IF NOT EXISTS idx_infer_created
    ON inference_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_infer_model
    ON inference_logs (model_name);
