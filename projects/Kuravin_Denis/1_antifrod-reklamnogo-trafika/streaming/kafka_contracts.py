"""
Контракты и спецификации для подсистемы стриминга Apache Kafka.
"""
from typing import Dict, Any

KAFKA_TOPICS = {
    "RAW_CLICKS": "clicks.raw",
    "FRAUD_ALERTS": "clicks.fraud",
    "DEAD_LETTER_QUEUE": "clicks.dlq"
}

CONSUMER_GROUPS = {
    "DETECTION_WORKERS": "ad-fraud-detector-workers",
    "ANALYTICS_SINK": "ad-clickhouse-analytics-sink"
}

# Пример структуры сообщения в clicks.raw
RAW_CLICK_MESSAGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "RawClickEvent",
    "type": "object",
    "properties": {
        "click_id": {"type": "string", "format": "uuid"},
        "publisher_id": {"type": "string"},
        "campaign_id": {"type": "string"},
        "user_id": {"type": "string"},
        "ip_address": {"type": "string", "format": "ipv4"},
        "user_agent": {"type": "string"},
        "timestamp": {"type": "number"},
        "url": {"type": "string"},
        "referer": {"type": ["string", "null"]},
        "device_type": {"type": "string"},
        "os": {"type": "string"},
        "geo_country": {"type": "string"},
        "click_interval_ms": {"type": "integer"}
    },
    "required": ["click_id", "publisher_id", "campaign_id", "ip_address", "timestamp"]
}

# Пример структуры сообщения в clicks.fraud
FRAUD_ALERT_MESSAGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "FraudAlertMessage",
    "type": "object",
    "properties": {
        "click_id": {"type": "string"},
        "is_fraud": {"type": "boolean"},
        "fraud_score": {"type": "number"},
        "status": {"type": "string", "enum": ["ALLOWED", "SUSPICIOUS", "BLOCKED"]},
        "primary_reason": {"type": "string"},
        "matched_rules": {"type": "array", "items": {"type": "string"}},
        "evaluated_at": {"type": "number"}
    },
    "required": ["click_id", "is_fraud", "fraud_score", "status"]
}
