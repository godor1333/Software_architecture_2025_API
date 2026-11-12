-- Схема аналитического хранилища
CREATE TABLE IF NOT EXISTS moderation_verdicts (
    id          BIGSERIAL PRIMARY KEY,
    post_id     UUID NOT NULL,
    decision    VARCHAR(16) NOT NULL CHECK (decision IN ('approve', 'flag', 'reject')),
    category    VARCHAR(32) NOT NULL DEFAULT 'none',
    scores      JSONB NOT NULL DEFAULT '{}',
    reasons     TEXT[] NOT NULL DEFAULT '{}',
    policy      VARCHAR(32) NOT NULL DEFAULT 'standard',
    trace       TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_verdicts_post_id ON moderation_verdicts (post_id);
CREATE INDEX IF NOT EXISTS ix_verdicts_decision ON moderation_verdicts (decision);
CREATE INDEX IF NOT EXISTS ix_verdicts_category ON moderation_verdicts (category);
CREATE INDEX IF NOT EXISTS ix_verdicts_created_at ON moderation_verdicts (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_verdicts_scores_gin ON moderation_verdicts USING GIN (scores);

CREATE TABLE IF NOT EXISTS media_objects (
    id          BIGSERIAL PRIMARY KEY,
    post_id     UUID NOT NULL,
    media_key   VARCHAR(512) NOT NULL,
    phash       VARCHAR(64),
    size_bytes  BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_media_phash ON media_objects (phash);
CREATE INDEX IF NOT EXISTS ix_media_post_id ON media_objects (post_id);
