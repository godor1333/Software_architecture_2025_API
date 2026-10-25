from fastapi.testclient import TestClient

from app.main import app, ml_adapter


client = TestClient(app)


def test_high_risk_order_is_sent_to_review() -> None:
    payload = {
        "order_id": "ord-001",
        "account_id": "acc-100",
        "device_id": "dev-77",
        "event_id": "concert-42",
        "ticket_count": 6,
        "amount": 42000,
        "purchase_attempts_10m": 5,
        "account_age_days": 1,
        "device_accounts_24h": 3,
    }
    response = client.post("/api/v1/orders/score", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["risk_score"] >= 0.15
    assert body["decision"] == "REVIEW"
    assert {item["code"] for item in body["reasons"]} == {
        "HIGH_VELOCITY",
        "BULK_PURCHASE",
        "FRESH_ACCOUNT",
        "SHARED_DEVICE",
    }


def test_low_risk_order_is_allowed_and_can_be_retrieved() -> None:
    payload = {
        "order_id": "ord-002",
        "account_id": "acc-200",
        "device_id": "dev-10",
        "event_id": "concert-42",
        "ticket_count": 2,
        "amount": 5400,
        "purchase_attempts_10m": 1,
        "account_age_days": 100,
        "device_accounts_24h": 1,
    }
    response = client.post("/api/v1/orders/score", json=payload)
    assert response.status_code == 201
    assert response.json()["decision"] == "ALLOW"
    retrieved = client.get("/api/v1/orders/ord-002")
    assert retrieved.status_code == 200
    assert retrieved.json()["order_id"] == "ord-002"


def test_invalid_ticket_count_is_rejected() -> None:
    payload = {
        "order_id": "ord-003",
        "account_id": "acc-300",
        "device_id": "dev-11",
        "event_id": "concert-42",
        "ticket_count": 0,
        "amount": 5400,
        "purchase_attempts_10m": 1,
        "account_age_days": 100,
        "device_accounts_24h": 1,
    }
    assert client.post("/api/v1/orders/score", json=payload).status_code == 422


def test_ml_features_have_safe_defaults() -> None:
    payload = {
        "order_id": "ord-004",
        "account_id": "acc-400",
        "device_id": "dev-12",
        "event_id": "concert-42",
        "ticket_count": 1,
        "amount": 2500,
        "purchase_attempts_10m": 1,
        "account_age_days": 30,
        "device_accounts_24h": 1,
    }
    response = client.post("/api/v1/orders/score", json=payload)
    assert response.status_code == 201
    assert 0 <= response.json()["risk_score"] <= 1


def test_trained_model_is_available_for_api_scoring() -> None:
    assert ml_adapter is not None


def test_dashboard_page_is_available() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "TicketShield" in response.text
    assert "дашборд антифрода" in response.text
