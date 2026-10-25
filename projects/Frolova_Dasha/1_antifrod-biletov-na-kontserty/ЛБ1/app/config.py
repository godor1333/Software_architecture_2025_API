from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Configuration shared by the API and the event-processing workers."""

    app_mode: str
    kafka_bootstrap_servers: str
    postgres_dsn: str
    redis_url: str
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    model_version: str
    decision_threshold: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_mode=os.getenv("APP_MODE", "local").lower(),
            kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            postgres_dsn=os.getenv(
                "POSTGRES_DSN", "postgresql://antifraud:antifraud@localhost:5432/antifraud"
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            clickhouse_host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            clickhouse_user=os.getenv("CLICKHOUSE_USER", "antifraud"),
            clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", "antifraud"),
            model_version=os.getenv("MODEL_VERSION", "lightgbm-1.0"),
            decision_threshold=float(os.getenv("DECISION_THRESHOLD", "0.15")),
        )


TOPIC_ORDERS_CREATED = "orders.created"
TOPIC_ORDERS_ENRICHED = "orders.enriched"
TOPIC_DECISIONS = "antifraud.decisions"
GROUP_FEATURES = "feature-service"
GROUP_SCORING = "scoring-service"
GROUP_ANALYTICS = "analytics-service"
