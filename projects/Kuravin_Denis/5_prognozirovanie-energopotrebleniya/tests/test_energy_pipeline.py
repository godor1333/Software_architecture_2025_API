import pytest
from fastapi.testclient import TestClient
from project_5_energy_consumption_forecasting.api.main import app, pipeline, repository, dispatch_observer
from project_5_energy_consumption_forecasting.models import MeterReadingEvent, AnomalySeverity
from project_5_energy_consumption_forecasting.ml.feature_pipeline import TimeSeriesFeaturePipeline
from project_5_energy_consumption_forecasting.ml.anomaly_detector import EnergyAnomalyDetector
from project_5_energy_consumption_forecasting.patterns.circuit_breaker import CircuitBreaker, CircuitState

client = TestClient(app)

def test_feature_pipeline_extraction():
    feats = TimeSeriesFeaturePipeline.extract_features(
        hour=14,
        day_of_week=2,
        temp_c=25.0,
        humidity_pct=45.0,
        lag_1h=450.0,
        lag_24h=420.0,
        rolling_mean_6h=440.0
    )
    vec = TimeSeriesFeaturePipeline.feature_vector(feats)

    assert len(vec) == 11
    assert feats["is_weekend"] == 0.0
    assert feats["temp_effect"] == 49.0  # (25-18)^2

def test_anomaly_detector_thresholds():
    detector = EnergyAnomalyDetector(residual_std=10.0, peak_limit_kw=800.0)

    # 1. Норма
    sev1, _, z1, _ = detector.evaluate("BLD-1", actual_kwh=300.0, predicted_kwh=295.0, timestamp=0.0)
    assert sev1 == AnomalySeverity.NORMAL
    assert z1 < 1.8

    # 2. Предупреждение (Warning)
    sev2, _, z2, _ = detector.evaluate("BLD-1", actual_kwh=320.0, predicted_kwh=300.0, timestamp=0.0)
    assert sev2 == AnomalySeverity.WARNING

    # 3. Критический пик (Critical Peak)
    sev3, _, z3, _ = detector.evaluate("BLD-1", actual_kwh=850.0, predicted_kwh=400.0, timestamp=0.0)
    assert sev3 == AnomalySeverity.CRITICAL_PEAK

def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=2, recovery_time_sec=0.1)

    def faulty():
        raise ConnectionError("Kafka timeout")

    with pytest.raises(ConnectionError):
        cb.call(faulty)
    with pytest.raises(ConnectionError):
        cb.call(faulty)

    assert cb.state == CircuitState.OPEN
    # Fallback при открытой цепи
    res = cb.call(faulty, fallback=lambda: "FALLBACK_OK")
    assert res == "FALLBACK_OK"

def test_pipeline_and_dispatch_observer():
    dispatch_observer.dispatched_alerts.clear()

    # Аварийная перегрузка
    ev = MeterReadingEvent(
        building_id="TEST-BUILDING",
        meter_reading_kwh=950.0,
        outside_temp_c=20.0
    )
    alert = pipeline.execute(ev)

    assert alert.severity == AnomalySeverity.CRITICAL_PEAK
    assert len(dispatch_observer.dispatched_alerts) >= 1
    assert dispatch_observer.dispatched_alerts[-1].building_id == "TEST-BUILDING"

def test_api_endpoints():
    # 1. Health
    h_resp = client.get("/api/v1/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "healthy"

    # 2. Record
    rec_payload = {
        "building_id": "BLD-API",
        "meter_reading_kwh": 350.0,
        "outside_temp_c": 18.0,
        "humidity_pct": 50.0
    }
    r_resp = client.post("/api/v1/energy/record", json=rec_payload)
    assert r_resp.status_code == 200
    assert "severity" in r_resp.json()

    # 3. Forecast
    fc_payload = {
        "building_id": "BLD-API",
        "horizon_hours": 4
    }
    f_resp = client.post("/api/v1/energy/forecast", json=fc_payload)
    assert f_resp.status_code == 200
    data = f_resp.json()
    assert len(data["points"]) == 4
    assert data["predicted_peak_kwh"] > 0

    # 4. Stats
    s_resp = client.get("/api/v1/energy/stats/BLD-API")
    assert s_resp.status_code == 200
    assert s_resp.json()["total_telemetry_points"] >= 1
