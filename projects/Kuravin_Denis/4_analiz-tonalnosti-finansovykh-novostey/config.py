import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "Financial News Sentiment & Entity Analysis Service"
    app_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # API
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8003"))

    # Kafka
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_raw: str = "financial.news.raw"
    kafka_topic_sentiment: str = "financial.news.sentiment"
    kafka_topic_alerts: str = "financial.news.alerts"
    kafka_consumer_group: str = "sentiment-analysis-workers"

    # Elasticsearch
    elasticsearch_hosts: str = os.getenv("ELASTICSEARCH_HOSTS", "http://localhost:9200")
    elasticsearch_index: str = "financial-news-index"

    # ClickHouse
    clickhouse_host: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    clickhouse_port: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    clickhouse_db: str = os.getenv("CLICKHOUSE_DB", "finance_analytics")

    # Alerting & Sentiment Thresholds
    alert_negative_threshold: float = 0.65
    positive_score_cutoff: float = 0.55
    negative_score_cutoff: float = 0.55

    # Fallback
    use_inmemory_fallback: bool = True

settings = Settings()
