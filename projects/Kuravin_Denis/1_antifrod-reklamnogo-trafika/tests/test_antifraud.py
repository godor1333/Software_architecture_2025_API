import pytest
from fastapi.testclient import TestClient
from project_1_ad_antifraud.api.main import app, evaluate_click_pipeline
from project_1_ad_antifraud.models import ClickEvent, FraudStatus
from project_1_ad_antifraud.patterns.circuit_breaker import CircuitBreaker, CircuitState

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["circuit_breaker_state"] == "CLOSED"

def test_blacklist_ip_blocked():
    ev = ClickEvent(
        publisher_id="pub_1",
        campaign_id="cmp_1",
        user_id="u1",
        ip_address="198.51.100.24",  # Blacklisted
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        url="https://example.com"
    )
    res = evaluate_click_pipeline(ev)
    assert res.is_fraud is True
    assert res.status == FraudStatus.BLOCKED
    assert "RULE_IP_BLACKLIST" in res.matched_rules

def test_bot_user_agent_blocked():
    ev = ClickEvent(
        publisher_id="pub_1",
        campaign_id="cmp_1",
        user_id="u2",
        ip_address="95.161.22.10",
        user_agent="python-requests/2.31.0",
        url="https://example.com"
    )
    res = evaluate_click_pipeline(ev)
    assert res.is_fraud is True
    assert res.status == FraudStatus.BLOCKED
    assert any("RULE_UA_BOT" in r for r in res.matched_rules)

def test_legitimate_click_allowed():
    ev = ClickEvent(
        publisher_id="pub_10",
        campaign_id="cmp_5",
        user_id="u_legit",
        ip_address="85.140.2.45",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        url="https://example.com",
        click_interval_ms=3500
    )
    res = evaluate_click_pipeline(ev)
    assert res.fraud_score < 0.65
    assert res.status in (FraudStatus.ALLOWED, FraudStatus.SUSPICIOUS)

def test_batch_api_endpoint():
    payload = {
        "events": [
            {
                "publisher_id": "pub_1",
                "campaign_id": "cmp_1",
                "user_id": "u1",
                "ip_address": "198.51.100.24",
                "user_agent": "curl/7.88.1",
                "url": "https://example.com",
                "click_interval_ms": 50
            },
            {
                "publisher_id": "pub_2",
                "campaign_id": "cmp_1",
                "user_id": "u2",
                "ip_address": "94.25.170.12",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "url": "https://example.com",
                "click_interval_ms": 4000
            }
        ]
    }
    resp = client.post("/api/v1/clicks/batch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["blocked_count"] >= 1

def test_metrics_endpoint():
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    assert "total_processed" in metrics
    assert "fraud_rate_percentage" in metrics

def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_time_sec=0.2)

    def failing_service():
        raise ConnectionError("Service unreachable")

    def fallback_service():
        return "FALLBACK_DATA"

    # Вызов 1: ошибка
    with pytest.raises(ConnectionError):
        cb.call(failing_service)
    assert cb.state == CircuitState.CLOSED

    # Вызов 2: вторая ошибка -> переход в OPEN
    with pytest.raises(ConnectionError):
        cb.call(failing_service)
    assert cb.state == CircuitState.OPEN

    # Вызов с fallback в состоянии OPEN
    res = cb.call(failing_service, fallback=fallback_service)
    assert res == "FALLBACK_DATA"
