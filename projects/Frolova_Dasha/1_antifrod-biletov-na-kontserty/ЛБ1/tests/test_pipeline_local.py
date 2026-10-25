import asyncio

from fastapi.testclient import TestClient

from app.config import Settings
from app.events import decode_message, encode_message
from app.main import build_app
from app.resilience import CircuitBreaker, CircuitOpenError, CircuitState
from app.schemas import OrderEvent
from app.storage import InMemoryCounterStore


def local_settings() -> Settings:
    return Settings(
        app_mode="local",
        kafka_bootstrap_servers="localhost:9092",
        postgres_dsn="postgresql://unused",
        redis_url="redis://unused",
        clickhouse_host="unused",
        clickhouse_port=8123,
        clickhouse_user="unused",
        clickhouse_password="unused",
        model_version="lightgbm-1.0",
        decision_threshold=0.15,
    )


def high_risk_payload(order_id: str = "ord-pipeline-local") -> dict:
    return {
        "order_id": order_id,
        "account_id": "acc-pipeline",
        "device_id": "dev-pipeline",
        "event_id": "concert-42",
        "ticket_count": 6,
        "amount": 42000,
        "purchase_attempts_10m": 5,
        "account_age_days": 1,
        "device_accounts_24h": 3,
    }


def test_event_message_roundtrip_uses_utf8_json() -> None:
    message = {"description": "Проверка кириллицы", "order_id": "ord-utf8"}
    encoded = encode_message(message)
    assert b"\\u" not in encoded
    assert decode_message(encoded) == message


def test_local_pipeline_persists_result_and_populates_dashboard() -> None:
    with TestClient(build_app(local_settings())) as client:
        response = client.post("/api/v1/orders/score", json=high_risk_payload())
        assert response.status_code == 201
        assert response.json()["decision"] == "REVIEW"
        result = client.get("/api/v1/orders/ord-pipeline-local")
        assert result.status_code == 200
        dashboard = client.get("/api/v1/dashboard/summary")
        assert dashboard.status_code == 200
        assert dashboard.json() == {
            "total_events": 1,
            "review_events": 1,
            "review_rate": 1.0,
            "average_risk_score": response.json()["risk_score"],
            "model_version": "lightgbm-1.0",
        }


def test_local_feature_store_leaves_explicit_features_intact() -> None:
    store = InMemoryCounterStore()
    event = OrderEvent.model_validate(high_risk_payload())
    assert asyncio.run(store.enrich(event)) == event


def test_circuit_breaker_opens_after_external_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=60)

    async def unavailable() -> None:
        raise ConnectionError("Kafka is unavailable")

    for _ in range(2):
        try:
            asyncio.run(breaker.call(unavailable))
        except ConnectionError:
            pass
    assert breaker.state == CircuitState.OPEN
    try:
        asyncio.run(breaker.call(unavailable))
    except CircuitOpenError:
        pass
    else:
        raise AssertionError("Circuit must reject calls while open")
