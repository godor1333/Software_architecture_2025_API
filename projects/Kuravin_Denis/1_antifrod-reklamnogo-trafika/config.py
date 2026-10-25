import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    app_name: str = "Ad Traffic Antifraud Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = os.getenv("ENVIRONMENT", "development")

    # API
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))

    # Kafka
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_raw: str = "clicks.raw"
    kafka_topic_fraud: str = "clicks.fraud"
    kafka_topic_dlq: str = "clicks.dlq"
    kafka_consumer_group: str = "ad-fraud-detector-group"

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_ttl_seconds: int = 3600

    # ClickHouse
    clickhouse_host: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    clickhouse_port: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    clickhouse_db: str = os.getenv("CLICKHOUSE_DB", "antifraud")

    # Scoring & Rules Thresholds
    fraud_threshold: float = 0.65
    suspicious_threshold: float = 0.40
    rate_limit_clicks_per_minute: int = 25
    rate_limit_clicks_per_hour: int = 150

    # Fallback mode
    use_mock_fallbacks_if_offline: bool = True

settings = Settings()
