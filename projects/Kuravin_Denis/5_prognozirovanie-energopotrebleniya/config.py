import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "Smart Building Energy Forecasting & Anomaly Service"
    app_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # API
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8004"))

    # Kafka
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_raw: str = "energy.telemetry.raw"
    kafka_topic_anomalies: str = "energy.telemetry.anomalies"
    kafka_topic_forecasts: str = "energy.forecasts"
    kafka_consumer_group: str = "energy-forecaster-workers"

    # ClickHouse / TimescaleDB
    clickhouse_host: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    clickhouse_port: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    clickhouse_db: str = os.getenv("CLICKHOUSE_DB", "energy_telemetry")

    # Anomaly Thresholds
    anomaly_z_score_threshold: float = 2.5
    warning_z_score_threshold: float = 1.8
    peak_overload_kw_threshold: float = 850.0

    # Fallback
    use_inmemory_fallback: bool = True

settings = Settings()
